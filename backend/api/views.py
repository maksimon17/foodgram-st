from django.urls import reverse
from rest_framework import viewsets, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.core.files.base import ContentFile
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
   permission_classes = [permissions.AllowAny]

   @action(detail=False, methods=['put'], url_path='me/avatar',
           permission_classes=[permissions.IsAuthenticated])
   def avatar(self, request):
       """Установка аватара пользователя."""
       user = request.user
       data = request.data.get('avatar')

       if not data:
           raise ValidationError('Вы не передали аватарку')

       try:
           format, imgstr = data.split(';base64,')
       except ValueError:
           raise ValidationError('Недопустимый формат аватарки')

       ext = format.split('/')[-1]
       file = ContentFile(base64.b64decode(imgstr),
                          name=f'avatar{user.id}.{ext}')
       user.avatar = file
       user.save()
       return Response({'avatar': user.avatar.url})

   @avatar.mapping.delete
   def delete_avatar(self, request):
       """Удаление аватара пользователя."""
       user = request.user

       if user.avatar and user.avatar.name != 'users/default_avatar.jpg':
           user.avatar.delete(save=False)
           user.avatar = 'users/default_avatar.jpg'
           user.save()

       return Response(status=status.HTTP_204_NO_CONTENT)

   @action(detail=True, methods=['post'],
           permission_classes=[permissions.IsAuthenticated])
   def subscribe(self, request, id=None):
       """Подписка на автора."""
       author = get_object_or_404(User, pk=id)
       if request.user == author:
           raise serializers.ValidationError(
               "Нельзя подписаться на самого себя."
           )
       _, created = Subscription.objects.get_or_create(
           user=request.user, author=author
       )
       if not created:
           raise serializers.ValidationError(
               f"Вы уже подписаны на пользователя {author.username}."
           )
       return Response(
           AuthorWithRecipesSerializer(author, context={'request': request}).data,
           status=status.HTTP_201_CREATED
       )

   @subscribe.mapping.delete
   def unsubscribe(self, request, id=None):
       """Отписка от автора."""
       get_object_or_404(
           Subscription, user=request.user, author_id=id
       ).delete()

       return Response(status=status.HTTP_204_NO_CONTENT)

   @action(detail=False, methods=['get'],
           permission_classes=[permissions.IsAuthenticated])
   def subscriptions(self, request):
       """Получение списка подписок."""
       subscriptions = Subscription.objects.filter(
           user=request.user
       ).select_related('author')

       queryset = [sub.author for sub in subscriptions]

       page = self.paginate_queryset(queryset)
       return self.get_paginated_response(AuthorWithRecipesSerializer(
           page, many=True, context={'request': request}
       ).data)


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
       recipe = get_object_or_404(Recipe, pk=recipe_id)

       if add:
           _, created = model.objects.get_or_create(user=user,
                                                    recipe=recipe)
           if not created:
               raise serializers.ValidationError(
                   f'Рецепт "{recipe.name}" уже добавлен.'
               )
           return Response(CompactRecipeSerializer(recipe).data,
                           status=status.HTTP_201_CREATED)

       get_object_or_404(model, user=user, recipe=recipe).delete()
       return Response(status=status.HTTP_204_NO_CONTENT)

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
       user = request.user
       ingredients = (
           RecipeIngredient.objects
           .filter(recipe__shopping_carts__user=user)  
           .values('ingredient__name', 'ingredient__measurement_unit')
           .annotate(total_amount=Sum('amount'))
           .order_by('ingredient__name')
       )

       recipes = Recipe.objects.filter(shopping_carts__user=user)

       shopping_list_content = generate_shopping_list(user, ingredients, recipes)

       return FileResponse(
           shopping_list_content,
           as_attachment=True,
           filename='shopping_list.txt',
           content_type='text/plain'
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
       queryset = Ingredient.objects.all().order_by('name')
       name = self.request.query_params.get('name', None)
       if name:
           queryset = queryset.filter(name__icontains=name)
       return queryset