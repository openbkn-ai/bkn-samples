# Energy local regression bank

100 bilingual question contracts and recovered historical structured projections.
The original independently generated oracle file was not retained in the temporary
source. `expected-results.json` contains a separately identified recovery baseline
from historical terminal submissions with original record SHA-256 provenance; it
is not represented as the lost original file. Required output fields are projected
explicitly; extra explanatory fields in old submissions are retained in the source
records but do not change the question contract.

Local replay validates against these historical projections and independent
hand-built boundary tests. It is not a new Agent run or a full-bank model-accuracy
claim, and does not combine targeted historical reruns into a new accuracy rate.
Question banks and answers remain in source and are excluded from installation
packages. Run `python bkn-eval/run.py` from the sample directory.
