from django.shortcuts import render

# Create your views here.
"""Creating view for recipe apis"""

from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from core.models import Recipe, Tag, Ingredient
from recipe import serializers
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)

from rest_framework.response import Response
from rest_framework.decorators import action

# Decorator to extend the schema documentation for specific view actions (like 'list') in a ViewSet
@extend_schema_view(

    # Specifies schema customization for the 'list' action (typically a GET request to list objects)
    list = extend_schema(

        # Adds custom query parameters that the API user can provide when listing items
        parameters = [

            # Defines the 'tags' query parameter (expected as comma-separated string of tag IDs)
            OpenApiParameter(
                'tags',  # The name of the query parameter
                OpenApiTypes.STR,  # The expected type (string)
                description = 'Comma separated List of IDS to filter',  # Description shown in API docs
            ),

            # Defines the 'ingredients' query parameter (also expected as a comma-separated string)
            OpenApiParameter(
                'ingredients',  # Typo fixed from 'ingredeints'
                OpenApiTypes.STR,  # The expected type (string)
                description = 'Comma separated list of ingredient IDS to filter',  # Help text in docs
            )
        ]
    )
)

class RecipeViewSet(viewsets.ModelViewSet):
    """View for manage recipe APIS"""

    serializer_class = serializers.RecipeDetailSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _params_to_ints(self, qs):
        """Convert a list of strings to ingegers"""
        return[int(str_id) for str_id in qs.split(',')]


    def get_queryset(self):
        tags = self.request.query_params.get('tags')
        ingredients = self.request.query_params.get('ingredients')
        queryset = self.queryset
        if tags:
            tag_ids = self._params_to_ints(tags)
            queryset = queryset.filter(tags__id__in=tag_ids)
        if ingredients:
            ingredient_ids = self._params_to_ints(ingredients)
            queryset = queryset.filter(ingredients__id__in = ingredient_ids)

        return queryset.filter(user=self.request.user).order_by('-id').distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.RecipeSerializer

        elif self.action == 'upload_image':
            return serializers.RecipeImageSerializer
        return self.serializer_class



    def perform_create(self, serializer):

        serializer.save(user = self.request.user)

    @action(methods = ['POST'], detail = True, url_path = 'upload_image')
    def upload_image(self, request, pk=None):
        """Upload an image to recipe"""
        recipe = self.get_object()
        serializer = self.get_serializer(recipe, data = request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema_view(
    list= extend_schema(
        parameters = [
            OpenApiParameter(
                'assigned_only',
                OpenApiTypes.INT, enum = [0,1],
                description = 'Filter by items assigned to recipes.',
            )
        ]
    )
)

class BaseRecipeAttrViewSet(mixins.DestroyModelMixin,
    mixins.UpdateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):

    """Base Viewset for recipe attributes"""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        """Return objects for the current authenticated user only, with optional filtering."""
        assigned_only = bool(
            int(self.request.query_params.get('assigned_only', 0))
        )

        queryset = self.queryset.filter(user=self.request.user)

        if assigned_only:
            queryset = queryset.filter(recipe__isnull=False)

        return queryset.order_by('-name').distinct()

class TagViewSet(BaseRecipeAttrViewSet):
    """Manage tags in database"""
    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()




class IngredientViewset(BaseRecipeAttrViewSet):

    serializer_class = serializers.IngredientSerializer
    queryset = Ingredient.objects.all()



