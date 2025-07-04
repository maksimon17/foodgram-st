from django.urls import reverse
from rest_framework import viewsets, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.core.files.base import ContentFile
from django.http import Http404
import base64
from core.models import (
    User, Ingredient, Recipe,
    Favorite, ShoppingCart, Subscription,
    RecipeIngredient
)
from api.serializers import (
    CustomUserSerializer,
    IngredientSerializer,
    RecipeSerializer,
    CompactRecipeSerializer,
    AuthorWithRecipesSerializer
)
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from api.pagination import PageLimitPagination
from api.filters import RecipeFilter
from django.core.exceptions import ValidationError
from djoser.views import UserViewSet
from rest_framework import serializers
from api.permissions import IsOwnerOrReadOnly
from api.shopping_cart_render import generate_shopping_list
from django.http import FileResponse
from django.db.models import Sum


class CustomUserViewSet(UserViewSet):
    """Расширенный ViewSet для работы с пользователями через Djoser"""
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    def get_permissions(self):
        """Настройка разрешений для разных действий"""
        if self.action in ['me', 'avatar', 'delete_avatar', 'subscribe', 'unsubscribe', 'subscriptions']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['put'], url_path='me/avatar')
    def avatar(self, request):
        """Установка аватара пользователя."""
        user = request.user
        data = request.data.get('avatar')

        if not data:
            return Response({'avatar': ['Это поле обязательно.']},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            format, imgstr = data.split(';base64,')
        except ValueError:
            return Response({'avatar': ['Недопустимый формат аватарки']},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            ext = format.split('/')[-1]
            file = ContentFile(base64.b64decode(imgstr),
                               name=f'avatar{user.id}.{ext}')
            user.avatar = file
            user.save()
            return Response({'avatar': user.avatar.url})
        except Exception as e:
            return Response({'avatar': ['Ошибка при обработке изображения']},
                            status=status.HTTP_400_BAD_REQUEST)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаление аватара пользователя."""
        user = request.user

        try:
            if user.avatar and user.avatar.name != 'users/default_avatar.jpg':
                user.avatar.delete(save=False)

            # Устанавливаем avatar в None вместо дефолтного изображения
            user.avatar = None
            user.save()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': 'Ошибка при удалении аватара'},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def subscribe(self, request, id=None):
        """Подписка на автора."""
        # Проверяем аутентификацию
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Учетные данные не были предоставлены.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Сначала проверяем существование автора - это должно вызвать 404 если не найден
        author = get_object_or_404(User, pk=id)

        if request.user == author:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        _, created = Subscription.objects.get_or_create(
            user=request.user, author=author
        )
        if not created:
            return Response(
                {'errors': f'Вы уже подписаны на пользователя {author.username}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            AuthorWithRecipesSerializer(
                author, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        """Отписка от автора."""
        # Проверяем аутентификацию
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Учетные данные не были предоставлены.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Сначала проверяем существование автора
        author = get_object_or_404(User, pk=id)

        try:
            subscription = Subscription.objects.get(
                user=request.user, author=author)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Subscription.DoesNotExist:
            return Response(
                {'errors': 'Подписка не найдена.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        """Получение списка подписок."""
        try:
            subscriptions = Subscription.objects.filter(
                user=request.user
            ).select_related('author')

            queryset = [sub.author for sub in subscriptions]

            page = self.paginate_queryset(queryset)
            if page is not None:
                return self.get_paginated_response(AuthorWithRecipesSerializer(
                    page, many=True, context={'request': request}
                ).data)

            return Response(AuthorWithRecipesSerializer(
                queryset, many=True, context={'request': request}
            ).data)
        except Exception as e:
            return Response(
                {'error': 'Ошибка при получении подписок'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с рецептами."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = PageLimitPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @staticmethod
    def manage_recipe_relation(model, user, recipe_id, add=True):
        """Универсальный метод для работы с избранным и корзиной"""
        # Не перехватываем Http404 - пусть она поднимается выше
        recipe = get_object_or_404(Recipe, pk=recipe_id)

        if add:
            _, created = model.objects.get_or_create(user=user, recipe=recipe)
            if not created:
                return Response(
                    {'errors': f'Рецепт "{recipe.name}" уже добавлен.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(CompactRecipeSerializer(recipe).data,
                            status=status.HTTP_201_CREATED)

        try:
            relation = model.objects.get(user=user, recipe=recipe)
            relation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except model.DoesNotExist:
            model_name = "избранного" if model == Favorite else "корзины"
            return Response(
                {'errors': f'Рецепт не найден в {model_name}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self.manage_recipe_relation(Favorite, request.user, pk, True)

    @favorite.mapping.delete
    def remove_favorite(self, request, pk=None):
        return self.manage_recipe_relation(Favorite, request.user, pk, False)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self.manage_recipe_relation(ShoppingCart, request.user, pk, True)

    @shopping_cart.mapping.delete
    def remove_shopping_cart(self, request, pk=None):
        return self.manage_recipe_relation(ShoppingCart, request.user, pk, False)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачивание списка покупок."""
        try:
            user = request.user
            ingredients = (
                RecipeIngredient.objects
                .filter(recipe__shopping_carts__user=user)
                .values('ingredient__name', 'ingredient__measurement_unit')
                .annotate(total_amount=Sum('amount'))
                .order_by('ingredient__name')
            )

            recipes = user.shopping_carts.all()

            shopping_list_content = generate_shopping_list(
                user, ingredients, recipes)

            return FileResponse(
                shopping_list_content,
                as_attachment=True,
                filename='shopping_list.txt',
                content_type='text/plain'
            )
        except Exception as e:
            return Response(
                {'error': 'Ошибка при создании списка покупок'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        """Получение короткой ссылки на рецепт."""
        if not Recipe.objects.filter(pk=pk).exists():
            return Response({'error': f'Рецепт с ID = {pk} не найден'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(
            {'short-link': request.build_absolute_uri(reverse(
                'recipe_redirect', args=[pk]
            ))},
            status=status.HTTP_200_OK
        )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для работы с ингредиентами."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    search_fields = ('^name',)

    def get_queryset(self):
        try:
            queryset = Ingredient.objects.all().order_by('name')
            name = self.request.query_params.get('name', None)
            if name:
                queryset = queryset.filter(name__icontains=name)
            return queryset
        except Exception as e:
            return Ingredient.objects.none()
