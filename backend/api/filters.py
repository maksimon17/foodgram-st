from django.db.models import OuterRef, Exists
from django_filters import rest_framework
from core.models import ShoppingCart, Favorite, Recipe


class RecipeFilter(rest_framework.FilterSet):
    """Фильтр для рецептов"""

    is_favorited = rest_framework.BooleanFilter(
        method='filter_is_favorited'
    )
    is_in_shopping_cart = rest_framework.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ['author', 'name']

    def filter_is_favorited(self, queryset, name, value):
        try:
            # Безопасная проверка аутентификации
            if not hasattr(self.request, 'user') or not self.request.user.is_authenticated:
                # Для незарегистрированных пользователей возвращаем пустой queryset для True
                # и полный queryset для False
                return queryset.none() if value else queryset

            favorite_exists = Exists(
                Favorite.objects.filter(user=self.request.user,
                                        recipe=OuterRef('pk'))
            )
            return queryset.filter(favorite_exists) if value else queryset.exclude(
                favorite_exists
            )
        except Exception:
            # В случае любой ошибки возвращаем исходный queryset
            return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        try:
            # Безопасная проверка аутентификации
            if not hasattr(self.request, 'user') or not self.request.user.is_authenticated:
                # Для незарегистрированных пользователей возвращаем пустой queryset для True
                # и полный queryset для False
                return queryset.none() if value else queryset

            in_cart_exists = Exists(
                ShoppingCart.objects.filter(user=self.request.user,
                                            recipe=OuterRef('pk'))
            )
            return queryset.filter(in_cart_exists) if value else queryset.exclude(
                in_cart_exists
            )
        except Exception:
            # В случае любой ошибки возвращаем исходный queryset
            return queryset
