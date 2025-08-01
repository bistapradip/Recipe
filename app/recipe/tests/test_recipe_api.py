"""
Test for recipe Api"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
import tempfile, os
from PIL import Image


from core.models import Recipe, Tag, Ingredient

from recipe.serializers import (RecipeSerializer, RecipeDetailSerializer)

RECIPES_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
    """Create amd return a recipe detail url"""

    return reverse('recipe:recipe-detail', args=[recipe_id])

def image_upload_url(recipe_id):
    """Create and return an image upload url"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    """Create recipe and return a sample recipe"""
    defaults = {
        'title': "Sample reciple title",
        "time_minutes": 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': "https://example.com/recipe.pdf",
    }

    defaults.update(params)

    recipe = Recipe.objects.create(user = user, **defaults)
    return recipe

def create_user(**params):
    """Create and return a new user"""

    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()


    def test_auth_required(self):
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
      #  self.user = create_user(email = "user@example.com", password = 'test123')
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testpass123',
        )

        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many = True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user."""
        other_user = get_user_model().objects.create_user(
            email='other@example.com',
            password ='password123'
        )

        create_recipe(user= other_user)
        create_recipe(user= self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user= self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)


    def test_create_recipe(self):
        """Test creating a recipe"""
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 30,
            'price': Decimal('5.99'),
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update of a recipe"""
        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user = self.user,
            title= 'Sampe recipe title',
            link = original_link,
        )
        payload = {'title': 'New recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of recipe"""

        recipe = create_recipe(
            user=self.user,
            title = 'Sample recipe tite',
            link = "https://example.com/recipe.pdf",
            description="Sampe recipe description",

        )

        payload = {
            'title': 'New recipe title',
            'link':  "https://example.com/new-recipe.pdf",
            'description': 'New recipe description',
            'time_minutes': 10,
            'price': Decimal('2.50'),

        }

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k),v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error"""
        new_user = create_user(email= "user2@example.com", password = "test123")

        recipe = create_recipe(user=self.user)
        payload = {'user':new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe sucesssful"""

        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())


    def test_recipe_other_users_recipe_errors(self):
        """Test trying to delete another users recipe gives error"""

        new_user = create_user(email='user2@example.com', password = 'test123')
        recipe = create_recipe(user = new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags"""

        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 20,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}],

        }

        res = self.client.post(RECIPES_URL,payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user = self.user)
       # Check that exactly one recipe was created for the user
        self.assertEqual(recipes.count(), 1)

        # Retrieve the created recipe instance from the queryset
        recipe = recipes[0]

        # Verify that two tags are associated with the created recipe
        self.assertEqual(recipe.tags.count(), 2)

        # Loop through each tag in the payload and check if it's correctly linked to the recipe
        for tag in payload['tags']:
        # Check if a tag with the same name and user exists in the recipe's tags
            exists = recipe.tags.filter(
            name=tag['name'],
            user=self.user,
            ).exists()

        # Assert that each tag from the payload has been successfully created and associated
        self.assertTrue(exists)


    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tag"""

        tag_indian = Tag.objects.create(user = self.user, name = 'Indian')
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('4.50'),
            'tags':  [
                {'name': 'Indian'},
                {'name': 'Breakfast'}
            ]
        }

        res = self.client.post(RECIPES_URL,payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name = tag['name'],
                user = self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating tag when updating a recipe"""
        recipe = create_recipe(user = self.user)

        payload = {'tags': [{'name': 'Lunch'}]}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name = 'Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe"""
        tag_breakfast = Tag.objects.create(user = self.user, name = "Breakfast")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)
        tag_lunch = Tag.objects.create(user = self.user, name = "Lunch")
        payload = {'tags': [{'name':'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())


    def test_clear_recipe_tags(self):
        """Test clearing a recipe tags"""
        tag = Tag.objects.create(user = self.user, name = "Dessert")
        recipe = create_recipe(user = self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.tags.count(), 0)


    def test_create_ingredient(self):
        """Testing the Create intgredient"""
        user = create_user(email = 'user4@example.com', password = 'pass123')
        ingredient = Ingredient.objects.create(
            user = user,
            name = 'Ingredient1'
        )

        self.assertEqual(str(ingredient), ingredient.name)

    def test_create_recipe_with_new_ingredients(self):
        """Creating a recipe with new ingredients"""
        payload = {
            'title': 'Cauliflowr',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [{'name': 'Cauliflower'}, {'name': 'Salt'}]

        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user = self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name = ingredient['name'],
                user = self.user,
            ).exists()
            self.assertTrue(exists)


    def test_create_recipe_with_existing_ingredients(self):
        ingredient = Ingredient.objects.create(user = self.user, name = "Lemon")

        payload = {
            'title': 'Soup',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [{'name': 'Lemon'}, {'name': 'Sauce'}]

        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user = self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user = self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when upddating a recipe"""
        recipe = create_recipe(user=self.user)
        payload = {'ingredients': [{
            'name': 'Limes'
        }
        ]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format = 'json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user = self.user, name = 'Limes')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient when updating a reciep"""
        ingredient1 = Ingredient.objects.create(user=self.user, name = 'Limes')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user = self.user, name = 'Chilli')
        payload = {'ingredients': [{'name': 'Chilli'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipe ingredients"""
        ingredient = Ingredient.objects.create(user = self.user, name = 'Garlic')
        recipe = create_recipe(self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        """Test filtering recipes by tags"""
        r1 = create_recipe(user = self.user, title = 'Thai Vegetable Curry')
        r2= create_recipe(user= self.user, title = 'Aubergine with Tahini')
        tag1 = Tag.objects.create(user = self.user, name = 'Vegan')
        tag2 = Tag.objects.create(user = self.user, name = 'Vegetarian')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=self.user, title = 'Fish and chips')

        params = {'tags': f'{tag1.id}, {tag2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """Test filtering recipes by ingedients"""
        r1 = create_recipe(user = self.user, title = 'Posh Beans on Toast')
        r2 = create_recipe(user = self.user, title = "Mushroom Soup")
        ing1 = Ingredient.objects.create(user = self.user, name = 'Salt')
        ing2 = Ingredient.objects.create(user = self.user, name = 'Pepper')
        r2.ingredients.add(ing2)
        r1.ingredients.add(ing1)

        r3 = create_recipe(user=self.user, title= 'Chickken')

        params = {'ingredients': f'{ing1.id}, {ing2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for the image upload API"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password1',
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user = self.user)

    def tearDown(self):
        self.recipe.image.delete()


    def test_upload_image(self):
        """Testing uploading an image to a recipe"""

        # Get the URL endpoint for uploading an image to a specific recipe
        url = image_upload_url(self.recipe.id)

        # Create a temporary file with .jpg suffix to simulate a real image file
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:

            # Create a blank 10x10 pixel RGB image using Pillow
            img = Image.new('RGB', (10, 10))

            # Save the image to the temporary file in JPEG format
            img.save(image_file, format='JPEG')

            # Move the file pointer back to the beginning so it can be read from
            image_file.seek(0)

            # Create a payload with the image file for POST request
            payload = {'image': image_file}

            # Send a POST request to upload the image
            res = self.client.post(url, payload, format='multipart')

        # Refresh the recipe instance from the database to get the updated image field
        self.recipe.refresh_from_db()

        # Assert that the upload was successful (HTTP 200 OK)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Assert that the response data includes the 'image' key
        self.assertIn('image', res.data)

        # Assert that the uploaded image file actually exists on disk
        self.assertTrue(os.path.exists(self.recipe.image.path))


    def test_upload_image_bad_request(self):
        """Tes uploading invalid image"""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)