"""Testing the ingredients of the recipe"""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer
from decimal import Decimal
INGREDIENTS_URL = reverse('recipe:ingredient-list')

def detail_url(ingredient_id):
    """Create and return an ingredient detail url"""
    return reverse('recipe:ingredient-detail', args = [ingredient_id])

def create_user(email = 'user@example.com', password = 'pass123'):
    """Create and return user"""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientsAPITest(TestCase):
    """Test the unauthenticated user for authorization"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retreiving the ingredients"""
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)



class PrivateIngredientsAPITest(TestCase):
    """Test the authenticated user for authorization"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_auth_retrieve_ingredients(self):
        """Test authenticated user can get ingredients"""
        Ingredient.objects.create(user=self.user, name = "Kale")
        Ingredient.objects.create(user= self.user, name = "Vanilla")

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many = True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredient_limited_to_user(self):
        """Test the ingredients is limted to the user"""

        user2 = create_user(email=  'user2@example.com')
        Ingredient.objects.create(user = user2, name = "Mushroom")
        ingredient = Ingredient.objects.create(user = self.user, name = "Salt")
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredients(self):
        """Test updating an ingredients"""
        ingredient = Ingredient.objects.create(user = self.user, name = 'BlaBla')

        payload = {'name': 'Cordinar'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredients(self):
        """Test deleting ingredients"""

        ingredient = Ingredient.objects.create(user = self.user, name = "Capciii")
        url = detail_url(ingredient.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user = self.user)
        self.assertFalse(ingredients.exists())


    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingredients bt those assigned to recipes"""
        int1 = Ingredient.objects.create(user = self.user, name = "Apples")
        int2 = Ingredient.objects.create(user = self.user, name = 'Turkey')
        recipe = Recipe.objects.create(
            title = 'Apple Crumble',
            time_minutes = 5,
            price = Decimal('2.56'),
            user = self.user
        )

        recipe.ingredients.add(int1)
        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        s1 = IngredientSerializer(int1)
        s2 = IngredientSerializer(int2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)


    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients returnss a unique list."""
        ing = Ingredient.objects.create(user = self.user, name = 'Eggs')
        Ingredient.objects.create(user = self.user, name = 'Lentils')
        recipe1 = Recipe.objects.create(
            title = 'Eggs Benedict',
            time_minutes = 60,
            price = Decimal('7.00'),
            user = self.user,
        )

        recipe2 = Recipe.objects.create(
            title = 'Herb Eggs',
            time_minutes = 20,
            price = Decimal('4.00'),
            user = self.user,
        )
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})


        self.assertEqual(len(res.data), 1)

