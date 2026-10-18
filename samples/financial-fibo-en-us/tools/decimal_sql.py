"""Exact financial arithmetic for the offline oracle, not runtime BKN functions."""
from decimal import Decimal,ROUND_HALF_UP,localcontext

def number(value):
    return Decimal(str(value))
def multiply(*values):
    if any(v is None for v in values):return None
    with localcontext() as ctx:
        ctx.prec=50
        result=Decimal(1)
        for v in values:result*=number(v)
        return str(result)
def rounded(value,places):
    if value is None:return None
    with localcontext() as ctx:
        ctx.prec=50
        return float(number(value).quantize(Decimal(1).scaleb(-int(places)),rounding=ROUND_HALF_UP))
class SumProduct:
    def __init__(self):self.total=Decimal(0);self.seen=False
    def step(self,*values):
        value=multiply(*values)
        if value is not None:
            with localcontext() as ctx:
                ctx.prec=50;self.total+=number(value);self.seen=True
    def finalize(self):return str(self.total) if self.seen else None
def register(db):
    db.create_function('DMUL',-1,multiply,deterministic=True)
    db.create_function('DSUB',2,lambda a,b:None if a is None or b is None else str(number(a)-number(b)),deterministic=True)
    db.create_function('DROUND',2,rounded,deterministic=True)
    db.create_aggregate('DSUM_PRODUCT',-1,SumProduct)
