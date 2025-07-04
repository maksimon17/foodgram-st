from django.shortcuts import redirect
from core.models import Recipe
from django.http import Http404


def recipe_redirect(request, recipe_id):
    """Перенаправляет на детальную страницу рецепта по ID."""
    try:
        recipe = Recipe.objects.get(id=recipe_id)
    except Recipe.DoesNotExist:
        raise Http404(f"Рецепт с ID={recipe_id} не найден")

    return redirect(f'/recipes/{recipe_id}/')
