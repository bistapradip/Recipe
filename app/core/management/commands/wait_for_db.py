# Django command to wait for the database to be available
from psycopg2 import OperationalError as Psycopg2pError
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand
import time

class Command(BaseCommand):
        
     def handle(self, *args, **options):
        self.stdout.write("Waiting for database...")
        db_up = False
        while db_up is False:
            try:
                self.check(databases=['default'])
                db_up = True
            except(Psycopg2pError, OperationalError):
                self.stdout.write("Databse unavailable, waiting 1 second...")
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS('Database available!'))

            


    
