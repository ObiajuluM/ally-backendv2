import time
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point, Polygon
from django.utils import timezone

# Adjust these imports based on your actual app names
# from config.models import (
#     User, Address, MyInformation, AllyAlert, AlertDelivery,
#     AlertReport, FirstResponder, UserDevice
# )
from ally.models import Address, MyInformation, User
from allyalert.models import AlertDelivery, AlertReport, AllyAlert
from firstresponder.models import FirstResponder
from servicearea.models import ServiceArea

# If FirstResponder is in a different app, import it from there.


class Command(BaseCommand):
    help = "Seeds the database with initial testing data centered around Port Harcourt, Nigeria."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Clearing existing data..."))
        # Clear existing data to avoid duplicates on multiple runs
        # AlertReport.objects.all().delete()
        # AlertDelivery.objects.all().delete()
        # AllyAlert.objects.all().delete()
        # FirstResponder.objects.all().delete()
        # ServiceArea.objects.all().delete()
        # UserDevice.objects.all().delete()
        # User.objects.all().delete()
        # MyInformation.objects.all().delete()
        # Address.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS("Database cleared. Starting seed process...")
        )
        self.stdout.write(
            self.style.NOTICE(
                "Note: This will take a moment due to Nominatim 1-req/sec rate limits."
            )
        )

        # ---------------------------------------------------------
        # 1. CREATE SERVICE AREA (Port Harcourt Bounding Box)
        # ---------------------------------------------------------
        # Coordinates roughly covering Port Harcourt mainland
        ph_poly = Polygon(
            (
                (6.9000, 4.7000),
                (7.1500, 4.7000),
                (7.1500, 4.9000),
                (6.9000, 4.9000),
                (6.9000, 4.7000),  # Close the polygon
            ),
            srid=4326,
        )

        ph_zone = ServiceArea.objects.create(
            name="Port Harcourt Metro Zone", polygon=ph_poly
        )
        self.stdout.write(self.style.SUCCESS(f"Created Service Area: {ph_zone.name}"))

        # ---------------------------------------------------------
        # 2. CREATE USERS & PROFILES
        # ---------------------------------------------------------
        users_data = [
            # {"email": "admin@ally.com", "username": "ally_admin", "is_superuser": True},
            {
                "email": "chidi@example.com",
                "username": "chidi_boy",
                "is_superuser": False,
            },
            {
                "email": "amaka@example.com",
                "username": "amaka_p",
                "is_superuser": False,
            },
        ]

        created_users = []
        for ud in users_data:
            # 1. Generate an address near PH center (Lon: 7.0498, Lat: 4.8156)
            lon = 7.0498 + random.uniform(-0.02, 0.02)
            lat = 4.8156 + random.uniform(-0.02, 0.02)

            addr = Address(location=Point(lon, lat, srid=4326))
            addr.save()
            time.sleep(1.5)  # REQUIRED: Respect Nominatim rate limits

            # 2. Create Profile
            info = MyInformation.objects.create(
                name=ud["username"].replace("_", " ").title(),
                address=addr,
                gender="Male" if "chidi" in ud["email"] else "Female",
                trusted_contacts=[
                    {"name": "Emergency Contact", "phone": "+2348012345678"}
                ],
            )

            # 3. Create User
            user = User.objects.create_user(
                email=ud["email"],
                username=ud["username"],
                password="password123",  # Default password for all
                is_superuser=ud["is_superuser"],
                is_staff=ud["is_superuser"],
                my_information=info,
                location=Point(lon, lat, srid=4326),
            )
            created_users.append(user)
            self.stdout.write(self.style.SUCCESS(f"Created User: {user.email}"))

        admin_user, chidi, amaka = created_users

        # ---------------------------------------------------------
        # 3. CREATE FIRST RESPONDERS
        # ---------------------------------------------------------
        responders = [
            {
                "name": "Rivers State Police Command (Moscow Road)",
                "type": "lawenforcement",
                "org": "government",
                "tags": ["police", "lawenforcement", "armedrobbery"],
                "lon": 7.0135,
                "lat": 4.7714,  # Actual rough coords for Moscow Road PH
            },
            {
                "name": "Braithwaite Memorial Specialist Hospital",
                "type": "firstaidandmedical",
                "org": "government",
                "tags": ["hospital", "health", "accident"],
                "lon": 7.0150,
                "lat": 4.7730,
            },
        ]

        for rd in responders:
            addr = Address(location=Point(rd["lon"], rd["lat"], srid=4326))
            addr.save()
            time.sleep(1.5)  # Nominatim limit

            fr = FirstResponder.objects.create(
                name=rd["name"],
                firstresponder_type=rd["type"],
                organization_type=rd["org"],
                address=addr,
                phones=["+2348000000000"],
                availability="24/7",
                tags=rd["tags"],
            )
            fr.service_areas.add(ph_zone)
            self.stdout.write(self.style.SUCCESS(f"Created First Responder: {fr.name}"))

        # ---------------------------------------------------------
        # 4. CREATE ALERTS
        # ---------------------------------------------------------
        alerts_data = [
            {
                "title": "Armed Robbery on Aba Road",
                "desc": "Suspected hoodlums attacking vehicles near Waterlines junction. Avoid the area.",
                "creator": chidi,
                "lon": 7.0252,
                "lat": 4.8150,
            },
            {
                "title": "Severe Flooding in GRA Phase 2",
                "desc": "Tombia street is heavily flooded. Cars are breaking down.",
                "creator": amaka,
                "lon": 7.0050,
                "lat": 4.8100,
            },
        ]

        created_alerts = []
        for ad in alerts_data:
            alert = AllyAlert(
                creator=ad["creator"],
                title=ad["title"],
                description=ad["desc"],
                created_location=Point(ad["lon"], ad["lat"], srid=4326),
                target_location=Point(ad["lon"] + 0.001, ad["lat"] + 0.001, srid=4326),
                radius_km=2.00,
                status="active",
            )
            alert.save()  # Triggers target_location geocode
            time.sleep(1.5)  # Nominatim limit
            created_alerts.append(alert)
            self.stdout.write(self.style.SUCCESS(f"Created Alert: {alert.title}"))

        # ---------------------------------------------------------
        # 5. CREATE DELIVERIES & REPORTS
        # ---------------------------------------------------------
        # Deliver Aba Road alert to Amaka
        AlertDelivery.objects.create(
            alert=created_alerts[0], user=amaka, viewed_at=timezone.now()
        )

        # Amaka reports Chidi's alert as helpful
        report = AlertReport.objects.create(
            alert=created_alerts[0],
            reporter=amaka,
            reason="helpful",
            description="Thanks, I just turned around.",
        )
        # Update the helpful count array on the alert
        created_alerts[0].helpful_count.append(amaka.id)
        created_alerts[0].save(update_fields=["helpful_count"])

        self.stdout.write(
            self.style.SUCCESS("Successfully seeded Deliveries and Reports.")
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Done! Database successfully seeded with Port Harcourt test data."
            )
        )
