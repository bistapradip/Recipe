""""
Serializer for recipe API"""

from rest_framework import serializers
from core.models import Recipe, Tag, Ingredient

class TagSerializer(serializers.ModelSerializer):
    """Serializer fot recipe detail view"""

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']

class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ['id', 'name']
        read_only_fields = ['id']




class RecipeSerializer(serializers.ModelSerializer):
    """Serializer of recipe"""

    tags = TagSerializer(many = True, required = False)
    ingredients = IngredientSerializer(many = True, required = False)

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_minutes', 'price','link', 'tags', 'ingredients']
        read_only_fields = ['id']

    # Helper method to get or create tags and assign them to a recipe
    def _get_or_create_tags(self, tags, recipe):
        """Handle getting or creating tags as needed"""

        # Get the currently authenticated user from the request context
        auth_user = self.context['request'].user

        # Loop through each tag in the incoming list
        for tag in tags:
            # Ensure the tag is a dictionary with a 'name' key (valid format)
            if isinstance(tag, dict) and 'name' in tag:
                # Try to get or create a Tag object for this user and tag data
                tag_obj, created = Tag.objects.get_or_create(
                    user=auth_user,
                    **tag,  # Unpack the dictionary (e.g., name='Breakfast')
                )
                # Add the tag to the recipe's many-to-many field
                recipe.tags.add(tag_obj)

    def _get_or_create_ingredients(self, ingredients, recipe):
        auth_user = self.context['request'].user

        for ingredient in ingredients:
            ingredient_obj, created = Ingredient.objects.get_or_create(
                user = auth_user,
                **ingredient,
            )
            recipe.ingredients.add(ingredient_obj)


    # Method to create a new recipe instance
    def create(self, validated_data):
        """Create a recipe"""

        # Extract tags from the validated data, or use empty list if not present
        tags = validated_data.pop('tags', [])
        ingredients = validated_data.pop('ingredients', [])


        # Create the recipe instance with the remaining validated fields
        recipe = Recipe.objects.create(**validated_data)

        # Associate the tags with the recipe using the helper method
        self._get_or_create_tags(tags, recipe)
        self._get_or_create_ingredients(ingredients, recipe)

        # Return the created recipe instance
        return recipe


    # Method to update an existing recipe instance
    def update(self, instance, validated_data):
        """Update recipe"""

        # Extract tags from the incoming data, if provided
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)

        if ingredients is not None:
            instance.ingredients.clear()
            self._get_or_create_ingredients(ingredients, instance)

        # If tags are provided, update the tags relationship
        if tags is not None:
            # Remove all current tags from the recipe
            instance.tags.clear()

            # Add new or existing tags back using the helper method
            self._get_or_create_tags(tags, instance)

        # Update other fields of the recipe (like title, time_minutes, price, etc.)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)  # Dynamically set attributes

        # Save the updated recipe instance to the database
        instance.save()

        # Return the updated recipe
        return instance






class RecipeDetailSerializer(RecipeSerializer):
    """Detail serializer of recipe"""

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + [
            'description',
        ]

class RecipeImageSerializer(serializers.ModelSerializer):
    """Serializer fpr uploading images to recipes"""

    class Meta:
        model = Recipe
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {'image': {'required': 'True'}}




