from planet import *
from planet_ui import show, compare

treatment = ExperimentVariable(name="treatment", options=["control", "experimental"])

design1 = (
    Design()
    .within_subjects(treatment)
    .counterbalance(treatment)
)

design2 = (
    Design()
    .between_subjects(treatment)
    .counterbalance(treatment)
)

compare(design1, design2, label1="Within-Subjects", label2="Between-Subjects", units=2)