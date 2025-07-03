import json
import os
from django.core.management.base import BaseCommand
from core.models import Ingredient


class Command(BaseCommand):
   help = "Импортирует ингредиенты из JSON-файла"

   def handle(self, *args, **kwargs):
       data_file = os.path.join("data", "ingredients.json")

       try:
           with open(data_file, encoding="utf-8") as file:
               ingredients_data = json.load(file)
               
           new_ingredients = []
           for item in ingredients_data:
               new_ingredients.append(Ingredient(**item))
               
           created_objects = Ingredient.objects.bulk_create(
               new_ingredients, ignore_conflicts=True
           )
           
           added_count = len(created_objects)
           
       except FileNotFoundError:
           self.stderr.write(self.style.ERROR(f"Файл {data_file} не найден!"))
           return
       except json.JSONDecodeError:
           self.stderr.write(self.style.ERROR(
               f"Некорректный JSON в файле {data_file}"
           ))
           return
       except Exception as e:
           self.stderr.write(self.style.ERROR(f"Произошла ошибка: {e}"))
           return

       self.stdout.write(
           self.style.SUCCESS(
               f"Импорт завершен успешно! Добавлено записей: {added_count}."
           )
       )