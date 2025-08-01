"""Tests for the tags API"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from core.models import Tag, Recipe
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')


def details_url(tag_id):
    """Create and return detail of tag """
    return reverse('recipe:tag-detail', args = [tag_id])

def create_user(email = "user@example.com", password = 'testpass123'):
    """Create and return a user"""
    return get_user_model().objects.create_user(email=email, password=password)

class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags"""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated api requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):

        Tag.objects.create(user=self.user, name = "Vegan")
        Tag.objects.create(user =self.user, name = "Dessert")

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many = True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user"""

        user2 = create_user(email="user2@example.com")
        Tag.objects.create(user = user2, name = 'Fruity')
        tag = Tag.objects.create(user= self.user, name = "Comfort Food")

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)



    def test_update_tags(self):
        """Test updating a tag"""
        tag = Tag.objects.create(user= self.user, name = 'After Dinner')

        payload = {
            'name': 'Dessert'
        }

        url = details_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Test Deleting a tag"""

        tag = Tag.objects.create(user = self.user, name = "Breakfast")
        url = details_url(tag.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user = self.user)
        self.assertFalse(tags.exists())


    def test_filter_tags_assigned_to_recipe(self):
        """Test listing tags by those assigned to recipes"""
        tag1 = Tag.objects.create(user=self.user, name = 'Vegan')
        tag2 = Tag.objects.create(user=self.user, name = 'Lunch')

        recipe = Recipe.objects.create(
            user = self.user,
            title=  'Paneer Recipe',
            time_minutes = 5,
            price = Decimal('3.5'),
            )

        recipe.tags.add(tag1)
        res = self.client.get(TAGS_URL, {'assigned_only': 1})
        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)


    def test_filter_tags_unique(self):

        tag1=Tag.objects.create(user = self.user, name = "Breakfast")
        Tag.objects.create(user = self.user, name = 'Lunch')

        recipe1 = Recipe.objects.create(
            title = 'Mushroom Soup',
            time_minutes = 5,
            price = Decimal('2.67'),
            user = self.user,
        )

        recipe2 = Recipe.objects.create(
            title = 'Panckaes',
            time_minutes = 6,
            price = Decimal('2.1'),
            user = self.user
        )

        recipe1.tags.add(tag1)
        recipe2.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only':1})

        self.assertEqual(len(res.data), 1)





