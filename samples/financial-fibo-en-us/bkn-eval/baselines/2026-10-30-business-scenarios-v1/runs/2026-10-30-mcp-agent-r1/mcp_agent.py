"""A plain external MCP agent: platform LLM (OpenAI-compatible) + every tool the 8081 BKN MCP server advertises.

One fresh MCP session per question; the answer set is never read; the token is never printed.
Usage: BKN_KN=financial_fibo_en_us python mcp_agent.py <question-set.yaml> <out-dir> [ids...] [--workers N] [--model M]
"""
import glob, json, os, subprocess, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import yaml

BASE = 'http://localhost:8081'
KN = os.environ.get('BKN_KN', 'supply_ontology_hand')
MAX_STEPS = 40
RESULT_CHARS = 30000


def token():
    p = glob.glob(os.path.expanduser('~/.bkn/platforms/aHR0cDovL2xvY2FsaG9zdDo4MDgx/users/*/token.json'))[0]
    return json.load(open(p))['accessToken']


def post(url, body, headers, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST',
                                 headers={'Authorization': 'Bearer ' + token(), 'Content-Type': 'application/json', **{k: v for k, v in headers.items() if k != '_retried'}})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.headers, r.read().decode()
    except urllib.error.HTTPError as e:
        if e.code != 401 or headers.get('_retried'):
            raise
        subprocess.run(['openbkn', 'auth', 'token'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return post(url, body, {**headers, '_retried': '1'}, timeout)


class MCP:
    URL = BASE + '/api/agent-retrieval/v1/mcp/'

    def __init__(self):
        self.sid, self.n = None, 0
        res = self.rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'eval-agent', 'version': '1'}})
        self.instructions = res.get('instructions', '')
        self.notify('notifications/initialized')
        self.tools = self.rpc('tools/list', {})['tools']

    def headers(self):
        h = {'x-kn-id': KN, 'Accept': 'application/json, text/event-stream', 'mcp-protocol-version': '2025-06-18'}
        if self.sid:
            h['mcp-session-id'] = self.sid
        return h

    def notify(self, method):
        post(self.URL, {'jsonrpc': '2.0', 'method': method}, self.headers())

    def rpc(self, method, params):
        self.n += 1
        hdrs, text = post(self.URL, {'jsonrpc': '2.0', 'id': self.n, 'method': method, 'params': params}, self.headers())
        self.sid = self.sid or hdrs.get('mcp-session-id')
        if not text.lstrip().startswith('{'):
            text = [l[5:] for l in text.splitlines() if l.startswith('data:')][-1]
        msg = json.loads(text)
        if 'error' in msg:
            raise RuntimeError(json.dumps(msg['error'], ensure_ascii=False))
        return msg['result']

    def call(self, name, args):
        try:
            res = self.rpc('tools/call', {'name': name, 'arguments': args})
        except Exception as e:  # tool errors go back to the model
            return 'ERROR: ' + str(e)[:2000]
        parts = [c.get('text', '') for c in res.get('content', []) if c.get('type') == 'text']
        out = '\n'.join(parts) or json.dumps(res.get('structuredContent'), ensure_ascii=False)
        return ('ERROR: ' if res.get('isError') else '') + out


def chat(model, messages, tools):
    _, text = post(BASE + '/api/mf-model-api/v1/chat/completions',
                   {'model': model, 'messages': messages, 'tools': tools, 'stream': False, 'max_tokens': 32000}, {}, timeout=900)
    choice = json.loads(text)['choices'][0]
    msg = choice['message']
    msg['_finish'] = choice.get('finish_reason')
    return msg


def ask(question, model):
    record = {'id': question['id'], 'question': question['question'], 'model': model, 'tools': [], 'answer': '', 'status': None}
    started = time.time()
    subprocess.run(['openbkn', 'auth', 'token'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # refresh before each question
    try:
        mcp = MCP()
        tools = [{'type': 'function', 'function': {'name': t['name'], 'description': t.get('description', ''),
                                                    'parameters': t.get('inputSchema') or {'type': 'object'}}} for t in mcp.tools]
        if KN.endswith(('_en', '_en_us')):
            system = ('You are an internal business Q&A assistant. Answer questions on knowledge network ' + KN + ' (kn_id) '
                      'with the BKN MCP tools. First use search_capabilities to find the skills and functions mounted on this '
                      'network, read the relevant skill and follow it. Answer only from tool results; never make anything up. '
                      'Answer in English.\n\nMCP server instructions:\n' + mcp.instructions)
        else:
            system = ('你是企业内部的业务问答助手，通过 BKN MCP 工具回答知识网络 ' + KN + '（kn_id）上的问题。'
                      '先用 search_capabilities 查这个网络挂载的技能和函数，读相关技能后按技能说明作答。'
                      '只依据工具返回的数据回答，不要编造。\n\nMCP 服务说明：\n' + mcp.instructions)
        messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': question['question']}]
        for _ in range(MAX_STEPS):
            msg = chat(model, messages, tools)
            record.setdefault('finishes', []).append([msg.pop('_finish', None), len(msg.get('content') or ''), len(msg.get('reasoning_content') or ''), len(msg.get('tool_calls') or [])])
            messages.append({k: v for k, v in msg.items() if v is not None})
            calls = msg.get('tool_calls') or []
            if not calls:
                if not (msg.get('content') or '').strip() and record.setdefault('empty_turns', 0) < 2:
                    # the model sometimes ends a turn with reasoning only; ask once more for the answer
                    record['empty_turns'] += 1
                    messages.append({'role': 'user', 'content': 'Give the final answer from the data already retrieved.' if KN.endswith(('_en', '_en_us')) else '请基于已经查到的数据给出最终回答。'})
                    continue
                record['answer'], record['status'] = msg.get('content') or '', 'answered'
                break
            for c in calls:
                try:
                    args = json.loads(c['function'].get('arguments') or '{}')
                except ValueError:
                    args = {}
                out = mcp.call(c['function']['name'], args)
                record['tools'].append({'name': c['function']['name'], 'input': args, 'output': out[:3000]})
                messages.append({'role': 'tool', 'tool_call_id': c['id'], 'content': out[:RESULT_CHARS]})
        else:
            record['status'] = 'step_limit'
    except Exception as e:
        record['status'] = 'client_error'; record['error'] = repr(e)[:1000]
    record['seconds'] = round(time.time() - started, 1)
    return record


def main():
    args = sys.argv[1:]
    opts = {'--workers': '3', '--model': 'deepseek-v4-flash'}
    for k in list(opts):
        if k in args:
            i = args.index(k); opts[k] = args[i + 1]; del args[i:i + 2]
    questions = yaml.safe_load(open(args[0], encoding='utf-8'))['questions']
    out = args[1]; os.makedirs(out, exist_ok=True)
    wanted = set(args[2:])
    todo = [q for q in questions if not wanted or q['id'] in wanted]

    def one(q):
        rec = ask(q, opts['--model'])
        json.dump(rec, open(os.path.join(out, q['id'] + '.json'), 'w'), ensure_ascii=False, indent=1)
        print(q['id'], rec['status'], f"{rec['seconds']}s", f"tools={len(rec['tools'])}", rec.get('error', '')[:200], flush=True)

    with ThreadPoolExecutor(int(opts['--workers'])) as pool:
        list(pool.map(one, todo))


if __name__ == '__main__':
    main()
