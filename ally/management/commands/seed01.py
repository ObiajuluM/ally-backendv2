# your_app/management/commands/seed.py

import random

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from faker import Faker

from ally.models import Address
from firstresponder.models import (
    FirstResponder,
    FirstResponderType,
    OrganizationType,
    FirstResponderTag,
)


fake = Faker()


class Command(BaseCommand):
    help = "Seed fake first responders"

    def handle(self, *args, **options):
        self.stdout.write("Seeding first responders...")

        # Lagos bounding box-ish area
        LAGOS_LAT_MIN = 6.40
        LAGOS_LAT_MAX = 6.70
        LAGOS_LNG_MIN = 3.20
        LAGOS_LNG_MAX = 3.60

        categories = list(FirstResponderType)
        organizations = list(OrganizationType)
        tags = list(FirstResponderTag)

        responders = []

        for i in range(100):
            latitude = random.uniform(
                LAGOS_LAT_MIN,
                LAGOS_LAT_MAX,
            )

            longitude = random.uniform(
                LAGOS_LNG_MIN,
                LAGOS_LNG_MAX,
            )

            category = random.choice(categories)

            # Generate a realistic-looking organization name
            organization_names = [
                "Lagos Emergency Response",
                "Lagos Community Safety",
                "Metro Emergency Services",
                "Rapid Response Nigeria",
                "SafeLife Emergency Services",
                "City Rescue Services",
                "Community Emergency Network",
                "Lagos Safety Initiative",
                "Emergency Support Centre",
                "Rapid Medical Response",
                "Community Rescue Network",
                "Urban Safety Services",
            ]

            name = (
                f"{random.choice(organization_names)} "
                f"{fake.city_suffix()}"
            )

            # ---------------------------------------------------------
            # Address
            # ---------------------------------------------------------

            address = Address.objects.create(
                location=Point(
                    longitude,
                    latitude,
                    srid=4326,
                ),
                as_string=fake.address(),
            )

            # ---------------------------------------------------------
            # First responder
            # ---------------------------------------------------------

            responder = FirstResponder.objects.create(
                name=name,
                firstresponder_type=category,
                organization_type=random.choice(organizations),
                description=fake.paragraph(
                    nb_sentences=3,
                ),
                phones=[
                    fake.phone_number(),
                    fake.phone_number(),
                ],
                availability=random.choice([
                    "24/7",
                    "Mon - Fri, 8AM - 5PM",
                    "Mon - Sun, 8AM - 10PM",
                    "Emergency Only",
                ]),
                response_time=random.choice([
                    "5-10 mins",
                    "10-15 mins",
                    "15-20 mins",
                    "20-30 mins",
                    "30-45 mins",
                ]),
                address=address,
                tags=random.sample(
                    tags,
                    k=random.randint(2, min(5, len(tags))),
                ),
                metadata={
                    "seeded": True,
                    "seed_version": 1,
                },
            )

            responders.append(responder)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {len(responders)} first responders."
            )
        )