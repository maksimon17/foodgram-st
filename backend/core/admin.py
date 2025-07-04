from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.safestring import mark_safe
from .models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
    Subscription,
    User
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Панель администрирования пользователей."""

    list_display = (
        'id', 'username', 'get_full_name', 'email', 'get_avatar_preview',
        'get_recipes_count', 'get_subscriptions_count', 'get_subscribers_count'
    )
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_active')

    @admin.display(description="Полное имя")
    def get_full_name(self, user):
        return f"{user.first_name} {user.last_name}"

    @admin.display(description="Аватарка")
    @mark_safe
    def get_avatar_preview(self, user):
        default_avatar = "/media/users/default_avatar.png"
        image_url = user.avatar.url if user.avatar else default_avatar
        return (
            f'<img src="{image_url}" width="50" '
            'height="50" style="border-radius: 50%;" />'
        )

    @admin.display(description="Количество рецептов")
    def get_recipes_count(self, user):
        return user.recipes.count()

    @admin.display(description="Число подписок")
    def get_subscriptions_count(self, user):
        return user.followers.count()

    @admin.display(description="Число подписчиков")
    def get_subscribers_count(self, user):
        return user.authors.count()


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Панель администрирования рецептов."""

    list_display = (
        'id', 'name', 'cooking_time', 'author', 'get_favorites_count',
        'get_ingredients_list', 'get_image_preview'
    )
    list_filter = ('author', 'cooking_time', 'date_published')
    search_fields = ('name', 'author__username')
    inlines = [RecipeIngredientInline]

    @admin.display(description="Добавлено в избранное")
    def get_favorites_count(self, recipe):
        return recipe.favorites.count()

    @admin.display(description="Список ингредиентов")
    @mark_safe
    def get_ingredients_list(self, recipe):
        return "<br>".join(
            f"{ingredient.name} ({ingredient.measurement_unit})"
            for ingredient in recipe.ingredients.all()
        )

    @admin.display(description="Изображение")
    @mark_safe
    def get_image_preview(self, recipe):
        if recipe.image:
            return f'<img src="{recipe.image.url}" width="80" height="50" />'
        return ""


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Панель администрирования ингредиентов."""

    list_display = ('name', 'measurement_unit', 'get_recipes_count')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit',)

    @admin.display(description="Использовано в рецептах")
    def get_recipes_count(self, ingredient):
        return ingredient.recipes.count()


@admin.register(Favorite, ShoppingCart)
class FavoriteAndShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    list_filter = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    list_filter = ('user', 'author')
    search_fields = ('user__username', 'author__username')
