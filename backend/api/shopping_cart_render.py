from django.utils.timezone import now


def generate_shopping_list(user, ingredients, recipes):
   """Создает текстовый список покупок для пользователя."""

   header = (
       f"Список покупок для {user.username}\n"
       f"Составлен: {now().strftime('%d-%m-%Y %H:%M:%S')}\n"
   )
   
   product_list = [
       f"{idx}. {item['ingredient__name'].capitalize()} "
       f"({item['ingredient__measurement_unit']}) - {item['total_amount']}"
       for idx, item in enumerate(ingredients, start=1)
   ]
   
   recipe_list = [
       f"- {recipe.name} (@{recipe.author.username})"
       for recipe in recipes
   ]
   
   final_text = '\n'.join([
       header,
       'Продукты:\n',
       *product_list,
       '\nРецепты, использующие эти продукты:\n',
       *recipe_list,
   ])
   
   return final_text