"""Idempotently creates a useful set of university staff departments."""
from django.core.management.base import BaseCommand
from staff_portal.models import StaffCategory, StaffDepartment


SEED = [
    (StaffCategory.TEACHING_SUPPORT, "Teaching Assistants & Tutorials", "Tutorial support and classroom assistance"),
    (StaffCategory.TEACHING_SUPPORT, "Academic Affairs", "Academic timetables and academic coordination"),
    (StaffCategory.TEACHING_SUPPORT, "Laboratory & Technical Support", "Laboratory demonstrations, instruments and technical support"),
    (StaffCategory.TEACHING_SUPPORT, "Examinations & Assessment", "Exam administration and assessment coordination"),
    (StaffCategory.TEACHING_SUPPORT, "E-Learning & Instructional Support", "Learning platforms and digital teaching support"),
    (StaffCategory.TEACHING_SUPPORT, "Academic Quality Assurance", "Teaching standards and quality monitoring"),
    (StaffCategory.TEACHING_SUPPORT, "Research Support", "Research operations and laboratory services"),
    (StaffCategory.TEACHING_SUPPORT, "School Administration", "Support services within academic schools"),
    (StaffCategory.NON_TEACHING, "Human Resources", "HR staffing, employment records and welfare"),
    (StaffCategory.NON_TEACHING, "Finance & Accounts", "Accounting, student finance and payments"),
    (StaffCategory.NON_TEACHING, "Admissions & Registry", "Student admissions and records"),
    (StaffCategory.NON_TEACHING, "Library Services", "Library lending and academic resources"),
    (StaffCategory.NON_TEACHING, "ICT Support", "IT infrastructure, networks and help desk"),
    (StaffCategory.NON_TEACHING, "Games & Sports", "Sports programmes, equipment and facilities"),
    (StaffCategory.NON_TEACHING, "Transport & Fleet", "University transport, drivers and vehicle coordination"),
    (StaffCategory.NON_TEACHING, "Security Services", "Campus safety and access control"),
    (StaffCategory.NON_TEACHING, "Estates & Maintenance", "Repairs and university grounds"),
    (StaffCategory.NON_TEACHING, "Hostel & Accommodation", "Residence management and room allocations"),
    (StaffCategory.NON_TEACHING, "Catering & Hospitality", "University food services and catering"),
    (StaffCategory.NON_TEACHING, "Procurement & Stores", "Purchases, stock and supply chain"),
    (StaffCategory.NON_TEACHING, "Student Welfare & Counselling", "Student wellbeing and counselling support"),
    (StaffCategory.NON_TEACHING, "Health Services", "Campus medical and occupational health services"),
    (StaffCategory.NON_TEACHING, "Communications & Public Relations", "University communications and public relations"),
    (StaffCategory.NON_TEACHING, "Cleaning & Grounds", "Custodial services and landscape maintenance"),
    (StaffCategory.NON_TEACHING, "Disability Support", "Accessibility and disability services"),
]


class Command(BaseCommand):
    help = "Add standard staff departments without changing existing departments or accounts."

    def handle(self, *args, **options):
        created_count = 0
        for category, name, description in SEED:
            _, created = StaffDepartment.objects.get_or_create(
                name=name,
                defaults={"category": category, "description": description, "is_active": True},
            )
            created_count += int(created)
        self.stdout.write(self.style.SUCCESS(
            f"Staff departments ready: {len(SEED)} templates, {created_count} new."
        ))
