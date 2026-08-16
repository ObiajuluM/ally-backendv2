import random
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.gis.geos import Point, Polygon
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from ally.models import Address, MyInformation, User
from allyalert.models import AlertDelivery, AlertReport, AllyAlert
from firstresponder.models import (
    FirstResponder,
    FirstResponderType,
    OrganizationType,
    FirstResponderTag,
)
from servicearea.models import ServiceArea

# from faker.config import AVAILABLE_LOCALES

# # This prints every valid string you can pass to Faker()
# print(AVAILABLE_LOCALES)


class Command(BaseCommand):
    help = "Seeds the database with test data centered around Port Harcourt, Nigeria using Faker."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of records to generate for each entity type (default: 100).",
        )

    def handle(self, *args, **options):
        count = options["count"]
        fake = Faker(["en_NG"])
        # fake = Faker(["en_NG", "en_US"])

        # self.stdout.write(self.style.WARNING("Clearing existing data..."))
        # AlertReport.objects.all().delete()
        # AlertDelivery.objects.all().delete()
        # AllyAlert.objects.all().delete()
        # FirstResponder.objects.all().delete()
        # ServiceArea.objects.all().delete()
        # User.objects.all().delete()
        # MyInformation.objects.all().delete()
        # Address.objects.all().delete()

        # self.stdout.write(self.style.SUCCESS("Database cleared."))
        self.stdout.write(
            self.style.NOTICE(
                f"Starting seed process for {count} items per entity type..."
            )
        )

        # ------------------------------------------------------------------
        # MOCK GEOLOCATOR
        # Mock Nominatim so save() methods don't make hundreds of HTTP requests
        # ------------------------------------------------------------------
        mock_address_obj = MagicMock()
        mock_address_obj.address = (
            f"{fake.street_name()}, Port Harcourt, Rivers State, Nigeria"
        )

        with patch("geopy.geocoders.Nominatim.reverse", return_value=mock_address_obj):

            # ---------------------------------------------------------
            # 1. CREATE SERVICE AREAS
            # ---------------------------------------------------------
            service_areas = []
            for i in range(count):
                # Center around Port Harcourt (Lon: ~6.92-7.12, Lat: ~4.72-4.92)
                base_lon = round(random.uniform(6.9200, 7.1000), 4)
                base_lat = round(random.uniform(4.7200, 4.9000), 4)
                offset = 0.02

                poly = Polygon(
                    (
                        (base_lon, base_lat),
                        (base_lon + offset, base_lat),
                        (base_lon + offset, base_lat + offset),
                        (base_lon, base_lat + offset),
                        (base_lon, base_lat),  # Close polygon
                    ),
                    srid=4326,
                )

                sa = ServiceArea.objects.create(
                    name=f"{fake.city_suffix()} Zone {i + 1} - {fake.street_name()}",
                    polygon=poly,
                )
                service_areas.append(sa)

            self.stdout.write(
                self.style.SUCCESS(f"Created {len(service_areas)} Service Areas.")
            )

            # ---------------------------------------------------------
            # 2. CREATE USERS & PROFILES
            # ---------------------------------------------------------
            users = []
            for _ in range(count):
                lon = round(random.uniform(6.9200, 7.1200), 6)
                lat = round(random.uniform(4.7200, 4.9200), 6)

                addr = Address(location=Point(lon, lat, srid=4326))
                addr.save()

                profile = MyInformation.objects.create(
                    name=fake.name(),
                    birthday=fake.date_of_birth(minimum_age=18, maximum_age=65),
                    address=addr,
                    gender=random.choice(["Male", "Female"]),
                    weight=random.uniform(50.0, 100.0),
                    height=random.uniform(150.0, 195.0),
                    allergies=random.sample(
                        ["Penicillin", "Peanuts", "Dust", "Latex"],
                        k=random.randint(0, 2),
                    ),
                    medications=random.sample(
                        ["Paracetamol", "Asthma Inhaler", "Vitamin C"],
                        k=random.randint(0, 1),
                    ),
                    trusted_contacts=[
                        {"name": fake.name(), "phone": fake.phone_number()}
                        for _ in range(random.randint(1, 3))
                    ],
                )

                username = fake.unique.user_name()
                user = User.objects.create_user(
                    email=f"{username}_{random.randint(100, 999)}@{fake.free_email_domain()}",
                    username=username,
                    password="password123",
                    phone=fake.unique.msisdn()[:15],
                    my_information=profile,
                    location=Point(lon, lat, srid=4326),
                )
                users.append(user)

            self.stdout.write(
                self.style.SUCCESS(f"Created {len(users)} Users & Profiles.")
            )

            # ---------------------------------------------------------
            # 3. CREATE FIRST RESPONDERS
            # ---------------------------------------------------------
            first_responders = []
            responder_types = [choice[0] for choice in FirstResponderType.choices]
            org_types = [choice[0] for choice in OrganizationType.choices]
            tag_choices = [choice[0] for choice in FirstResponderTag.choices]

            for _ in range(count):
                lon = round(random.uniform(6.9200, 7.1200), 6)
                lat = round(random.uniform(4.7200, 4.9200), 6)

                addr = Address(location=Point(lon, lat, srid=4326))
                addr.save()

                fr = FirstResponder.objects.create(
                    name=f"{fake.company()} Emergency Response",
                    firstresponder_type=random.choice(responder_types),
                    organization_type=random.choice(org_types),
                    description=fake.catch_phrase(),
                    address=addr,
                    phones=[fake.phone_number(), fake.phone_number()],
                    availability=random.choice(["24/7", "8am - 5pm", "Mon-Fri"]),
                    response_time=f"{random.randint(3, 20)} mins",
                    tags=random.sample(tag_choices, k=random.randint(1, 4)),
                )
                # Assign to 1-3 random service areas
                fr.service_areas.set(
                    random.sample(service_areas, k=random.randint(1, min(3, count)))
                )
                first_responders.append(fr)

            self.stdout.write(
                self.style.SUCCESS(f"Created {len(first_responders)} First Responders.")
            )

            # ---------------------------------------------------------
            # 4. CREATE ALERTS
            # ---------------------------------------------------------
            alerts = []
            alert_titles = [
                "Armed Robbery Reported",
                "Severe Road Accident",
                "Flash Flood Hazard",
                "Fire Outbreak in Commercial Building",
                "Suspicious Group Gathered",
                "Pipeline Vandalism Incident",
                "Gridlock / Traffic Blockade",
            ]

            status_choices = [
                AllyAlert.Status.ACTIVE,
                AllyAlert.Status.EXPIRED,
                AllyAlert.Status.REMOVED,
            ]

            for _ in range(count):
                creator = random.choice(users)
                c_lon = round(random.uniform(6.9200, 7.1200), 6)
                c_lat = round(random.uniform(4.7200, 4.9200), 6)
                t_lon = c_lon + random.uniform(-0.005, 0.005)
                t_lat = c_lat + random.uniform(-0.005, 0.005)

                alert = AllyAlert(
                    creator=creator,
                    title=f"{random.choice(alert_titles)} near {fake.street_name()}",
                    description=fake.paragraph(nb_sentences=3),
                    created_location=Point(c_lon, c_lat, srid=4326),
                    target_location=Point(t_lon, t_lat, srid=4326),
                    radius_km=round(random.uniform(0.5, 5.0), 2),
                    status=random.choice(status_choices),
                    expires_at=timezone.now() + timedelta(hours=random.randint(1, 72)),
                )
                alert.save()
                alerts.append(alert)

            self.stdout.write(self.style.SUCCESS(f"Created {len(alerts)} Ally Alerts."))

            # ---------------------------------------------------------
            # 5. CREATE DELIVERIES & REPORTS
            # ---------------------------------------------------------
            deliveries_count = 0
            delivery_pairs = set()

            for _ in range(count):
                alert = random.choice(alerts)
                user = random.choice(users)
                pair = (alert.id, user.id)

                if pair not in delivery_pairs:
                    delivery_pairs.add(pair)
                    AlertDelivery.objects.create(
                        alert=alert,
                        user=user,
                        viewed_at=(
                            timezone.now() if random.choice([True, False]) else None
                        ),
                    )
                    deliveries_count += 1

            reports_count = 0
            report_pairs = set()
            reason_choices = [choice[0] for choice in AlertReport.Reason.choices]

            for _ in range(count):
                alert = random.choice(alerts)
                reporter = random.choice(users)
                pair = (alert.id, reporter.id)

                if pair not in report_pairs:
                    report_pairs.add(pair)
                    reason = random.choice(reason_choices)

                    AlertReport.objects.create(
                        alert=alert,
                        reporter=reporter,
                        reason=reason,
                        description=fake.sentence(),
                    )

                    # Update alert helpful/report arrays
                    if reason == AlertReport.Reason.HELPFUL:
                        alert.helpful_count.append(reporter.id)
                        alert.save(update_fields=["helpful_count"])
                    else:
                        alert.report_count.append(reporter.id)
                        alert.save(update_fields=["report_count"])

                    reports_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {deliveries_count} Deliveries and {reports_count} Reports."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Database successfully seeded with {count} items per entity type."
            )
        )
