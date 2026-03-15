import random

from django.core.management.base import BaseCommand
from faker import Faker

from ally.models import (
    Address,
    FirstResponder,
    FirstResponderTag,
    FirstResponderType,
    MyInformation,
    OrganizationType,
    User,
)


class Command(BaseCommand):
    help = "Populate the database with fake users, personal information, and first responders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=10,
            help="Number of fake users to create.",
        )
        parser.add_argument(
            "--responders",
            type=int,
            default=20,
            help="Number of fake first responders to create.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Optional random seed for repeatable fake data.",
        )

    def handle(self, *args, **options):
        fake = Faker()
        seed = options["seed"]
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        users_count = max(options["users"], 0)
        responders_count = max(options["responders"], 0)

        created_users = 0
        created_responders = 0

        for _ in range(users_count):
            self.create_user(fake)
            created_users += 1

        for _ in range(responders_count):
            self.create_first_responder(fake)
            created_responders += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_users} users and {created_responders} first responders."
            )
        )

    def create_address(self, fake):
        return Address.objects.create(
            latitude=round(random.uniform(-90, 90), 6),
            longitude=round(random.uniform(-180, 180), 6),
            full_address=fake.address().replace("\n", ", "),
        )

    def create_my_information(self, fake):
        trusted_contacts = [
            self.make_trusted_contact(fake) for _ in range(random.randint(1, 3))
        ]
        is_pregnant = random.choice([True, False])

        return MyInformation.objects.create(
            name=fake.name(),
            birthday=fake.date_of_birth(minimum_age=18, maximum_age=80),
            address=self.create_address(fake),
            gender=random.choice(["male", "female", "non-binary", "prefer not to say"]),
            weight=round(random.uniform(45, 120), 1),
            height=round(random.uniform(145, 205), 1),
            allergies=random.sample(
                ["Peanuts", "Dust", "Penicillin", "Seafood", "None"],
                k=random.randint(1, 3),
            ),
            medications=random.sample(
                ["Ibuprofen", "Insulin", "Ventolin", "Paracetamol", "None"],
                k=random.randint(1, 3),
            ),
            medical_notes=fake.sentence(nb_words=12),
            organ_donor=random.choice([True, False]),
            is_pregnant=is_pregnant,
            due_date=(
                fake.date_between(start_date="today", end_date="+280d")
                if is_pregnant
                else None
            ),
            trusted_contacts=trusted_contacts,
        )

    def create_user(self, fake):
        my_information = self.create_my_information(fake)
        email = self.unique_email(fake)

        return User.objects.create_user(
            email=email,
            username=fake.user_name(),
            phone=self.unique_phone(fake),
            password="password123",
            my_information=my_information,
        )

    def create_first_responder(self, fake):
        responder_type = random.choice(FirstResponderType.values)
        org_type = random.choice(OrganizationType.values)
        tag_count = random.randint(1, 4)

        return FirstResponder.objects.create(
            name=f"{fake.company()} Response Unit",
            firstresponder_type=responder_type,
            organization_type=org_type,
            description=fake.text(max_nb_chars=180),
            phones=[self.unique_phone(fake) for _ in range(random.randint(1, 3))],
            availability=random.choice(["24/7", "Business hours", "Weekends only"]),
            socials={
                "facebook": fake.url(),
                "x": fake.url(),
                "website": fake.url(),
            },
            response_time=random.choice(["5 mins", "10 mins", "15 mins", "30 mins"]),
            address=self.create_address(fake),
            tags=random.sample(list(FirstResponderTag.values), k=tag_count),
            metadata={
                "service_area": fake.city(),
                "verified": random.choice([True, False]),
            },
        )

    def make_trusted_contact(self, fake):
        return {
            "name": fake.name(),
            "phone": self.unique_phone(fake),
        }

    def unique_email(self, fake):
        while True:
            email = fake.unique.email()
            if not User.objects.filter(email=email).exists():
                return email

    def unique_phone(self, fake):
        while True:
            phone = f"+234{random.randint(7000000000, 9099999999)}"
            if not User.objects.filter(phone=phone).exists():
                return phone
