"""Record only image identities from a candidate Chart rendered with defaults."""
import json
from pathlib import Path
import sys

import yaml


def verify(rendered, service_digest, version):
    deployments = [item for item in yaml.safe_load_all(rendered)
                   if item and item.get("kind") == "Deployment"
                   and item["metadata"]["name"] == "bkn-sample-studio"]
    if len(deployments) != 1:
        raise ValueError("expected one sample service Deployment")
    pod = deployments[0]["spec"]["template"]["spec"]
    studio = next(c for c in pod["containers"] if c["name"] == "studio")
    env = {e["name"]: e.get("value") for e in studio["env"]}
    expected = "swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-sample-studio@" + service_digest
    if studio["image"] != expected or env["BKN_SAMPLE_EXECUTOR_IMAGE_REF"] != expected:
        raise ValueError("Chart service/executor must use the verified SWR digest")
    if pod.get("imagePullSecrets"):
        raise ValueError("standard anonymous acceptance requires no pullSecrets")
    if env["BKN_SAMPLE_DATA_IMAGE_TAG"] != version or env["BKN_SAMPLE_DATA_IMAGE_REF"]:
        raise ValueError("legacy data image must resolve the verified candidate tag")
    return {"service": expected, "executor": expected, "pullSecrets": [],
            "data_tag": version, "data_reference_override": ""}


if __name__ == "__main__":
    value = verify(Path(sys.argv[1]).read_text(), sys.argv[2], sys.argv[3])
    Path(sys.argv[4]).write_text(json.dumps(value, indent=2) + "\n")
