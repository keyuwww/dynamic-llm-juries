# Confirmatory size (fixed Nov 20 from the pilot's yield, parse rate and cost only; no approval result was looked at)

Pilot (questions 0..79): 31 of 80 questions eligible (39%). Parser: 98-100% of each judge's own answers parsed; every
pilot pair has >= 5 parsed own answers for every judge; 1 of 124 verdicts unparsed. Billed $7.63: answer writing
$0.021 per question; verdicts + own answers $0.19 per pair.

Confirmatory set: questions 80..1879 (1,800 questions), expected about 700 pairs and 2,800 judgments: about $38
writing + $135 verdicts and own answers + about $70 for auditing every wrong response = about $245. Hard cap $300
(checked before every call, pilot spend included). The pilot is reported separately. Missing judgments (timeouts)
are reported as missing; the size is not changed after seeing results.

Parser change before the confirmatory run (pilot only, recorded in math_rep.py): the first parser read only the
integer after "Answer:" (else the last \boxed{}); on pilot answers it missed "The answer is \boxed{15}" written under
a "Final Answer:" heading and "the answer is $11$", so it now reads the integer after the LAST of "Answer:",
"answer is" or "\boxed{", with no fallback to an earlier marker.
