"""All student-facing calculations use the same source of financial truth."""
from decimal import Decimal
from django.db.models import Sum
from academics.models import ProgrammeUnit, StudentProgramme
from .models import (FeeCharge, FeePayment, StudentClearance,
                     FinalUnitResult, GraduationPolicy)

ZERO = Decimal("0.00")


def financial_statement(student):
    charges = list(FeeCharge.objects.filter(student=student).order_by("issued_at", "pk"))
    paid_by_charge = dict(FeePayment.objects.filter(charge__student=student)
        .values("charge_id").annotate(total=Sum("amount")).values_list("charge_id", "total"))
    rows = []
    tuition = hostel = other = paid = ZERO
    for charge in charges:
        received = paid_by_charge.get(charge.pk, ZERO) or ZERO
        paid += received
        if charge.category == FeeCharge.Category.HOSTEL:
            hostel += charge.amount
        elif charge.category == FeeCharge.Category.TUITION:
            tuition += charge.amount
        else:
            other += charge.amount
        rows.append({"charge": charge, "received": received,
                     "balance": charge.amount - received})
    total = tuition + hostel + other
    return {"rows": rows, "tuition": tuition, "hostel": hostel,
            "other": other, "total": total, "paid": paid,
            "balance": total - paid, "has_charges": bool(charges)}


def classification(student):
    """Compute a preview from VERIFIED final unit marks, never assignment marks.

    An award is withheld until all required programme units have final results.
    """
    record = StudentProgramme.objects.select_related("programme").filter(student=student).first()
    answer = {"record": record, "average": None, "label": None,
              "complete": False, "scheme": "MANUAL", "missing": 0, "failed": False}
    if not record:
        return answer
    placements = list(ProgrammeUnit.objects.filter(
        programme=record.programme, required=True).select_related("unit").order_by("pk"))
    required_ids = {p.pk for p in placements}
    marks = {r.placement_id: r.mark for r in FinalUnitResult.objects.filter(
        student=student, placement_id__in=required_ids, verified=True)}
    answer["missing"] = len(required_ids - set(marks))
    answer["complete"] = bool(placements) and answer["missing"] == 0
    policy = GraduationPolicy.objects.filter(programme=record.programme).first()
    if not policy:
        answer["label"] = "Awaiting university classification policy"
        return answer
    answer["scheme"] = policy.scheme
    if not answer["complete"]:
        answer["label"] = "Not yet classifiable"
        return answer
    weight = sum((p.unit.credits for p in placements), 0)
    if weight <= 0:
        answer["complete"] = False
        answer["label"] = "Unit credits require review"
        return answer
    average = sum((marks[p.pk] * p.unit.credits for p in placements), ZERO) / Decimal(weight)
    answer["average"] = average.quantize(Decimal("0.01"))
    answer["failed"] = any(mark < policy.pass_mark for mark in marks.values())
    if answer["failed"]:
        answer["label"] = "Failed compulsory unit / academic review required"
    elif average < policy.pass_mark:
        answer["label"] = "Below programme pass threshold"
    elif policy.scheme == GraduationPolicy.Scheme.MANUAL:
        answer["label"] = "Registrar determines final classification"
    elif policy.scheme == GraduationPolicy.Scheme.PASS_ONLY:
        answer["label"] = "Pass (subject to board approval)"
    elif average >= policy.first_class:
        answer["label"] = "First Class Honours (provisional)"
    elif average >= policy.upper_second:
        answer["label"] = "Second Class Honours (Upper Division) (provisional)"
    elif average >= policy.lower_second:
        answer["label"] = "Second Class Honours (Lower Division) (provisional)"
    else:
        answer["label"] = "Pass (provisional)"
    return answer


def graduation_readiness(student):
    record_info = classification(student)
    record = record_info["record"]
    finances = financial_statement(student)
    clear = StudentClearance.objects.filter(student=student).first()
    blockers = []
    if not record:
        blockers.append("No university programme is assigned")
    elif record.status != StudentProgramme.Status.COMPLETED:
        blockers.append("Programme has not been officially marked completed")
    if not record_info["complete"]:
        blockers.append("Required final results are missing or unverified")
    if record_info["average"] is None or record_info["failed"]:
        blockers.append("Academic assessment or compulsory-unit pass requirements are incomplete")
    policy = GraduationPolicy.objects.filter(programme=record.programme).first() if record else None
    if policy and record_info["average"] is not None and record_info["average"] < policy.pass_mark:
        blockers.append("Overall results are below the programme pass requirement")
    if not policy:
        blockers.append("Graduation policy not yet approved for this programme")
    if not finances["has_charges"]:
        blockers.append("Finance office has not issued a fee statement")
    if finances["balance"] > ZERO:
        blockers.append("Outstanding school or hostel fees")
    for field, label in (("finance", "Finance"), ("library", "Library"),
                         ("hostel", "Accommodation"), ("department", "Department")):
        if not clear or not getattr(clear, field):
            blockers.append(f"{label} clearance is pending")
    return {**record_info, "financial": finances, "clearance": clear,
            "blockers": blockers, "eligible": not blockers}
