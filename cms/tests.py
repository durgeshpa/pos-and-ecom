from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from cms import models

from django.contrib.auth import get_user_model
import pdb

class TestCard(APITestCase):

    def setUp(self):
        self.current_user = get_user_model().objects.create_user(phone_number='6266218245', password='goldfish1234')

        card_data_data = {
            "header": "new header",
            "header_action": "http://google.com",
            "sub_header": "subheading",
            "footer": "footer text",
            "scroll_type": "noscroll",
            "is_scrollable_x": True,
            "is_scrollable_y": False,
            "rows": 2,
            "cols": 2,
        }

        card_data_data_2 = {
            "header": "upgraded header",
            "header_action": "http://youtube.com",
            "sub_header": "subheading",
            "footer": "footer text",
            "scroll_type": "noscroll",
            "is_scrollable_x": True,
            "is_scrollable_y": False,
            "rows": 1,
            "cols": 1,
        }
        
        new_card_data = models.card_data.objects.create(**card_data_data)
        updated_card_date =  models.card_data.objects.create(**card_data_data_2)
        models.CardItem.objects.create(card_data=new_card_data,
                                        content="item1",
                                        priority=2,
                                        row=1
                                        )
        models.CardItem.objects.create(card_data=new_card_data,
                                        content="item2",
                                        priority=1,
                                        row=1
                                        )
        new_app = models.Application.objects.create(
            name="new app",
            created_by=self.current_user,
            status="Active"
        )

        new_card = models.Card.objects.create(name="new card", type="image", app=new_app)
        models.CardVersion.objects.create(
            version_number=1,
            card=new_card,
            card_data=new_card_data,
            created_by=self.current_user
        )
        models.CardVersion.objects.create(
            version_number=2,
            card=new_card,
            card_data=updated_card_date,
            created_by=self.current_user
        )

        card_post_json = {
            "app_id": 1,
            "name": "new new card",
            "type": "brand",
            "card_data": {
                # "image": "<url string>",
                "header": "new header",
                "header_action": "http://amazon.com",
                "sub_header": "new sub heading",
                "footer": "new footer text",
                "rows": 3,
                "cols": 2,
                "scroll_type": "button",
                "is_scrollable_x": True,
                "is_scrollable_y": False,
                "items": [
                    {
                        # "image": "<url_string>",
                        "content": "new content",
                        "priority": 1,
                        "row": 2
                    }
                ]
            }
        }
        url = reverse('cards')
        response = self.client.post(url, data=card_post_json, format="json")

   
    
    def test_create_new_card(self):
        """Ensure we can create cards"""

        card_post_json = {
            "app_id": "1",
            "name": "new new card",
            "type": "brand",
            "card_data": {
                # "image": "<url string>",
                "header": "new header",
                "header_action": "http://amazon.com",
                "sub_header": "new sub heading",
                "footer": "new footer text",
                "rows": 3,
                "cols": 2,
                "scroll_type": "button",
                "is_scrollable_x": True,
                "is_scrollable_y": False,
                "items": [
                    {
                        # "image": "<url_string>",
                        "content": "new content",
                        "priority": 1,
                        "row": 2
                    }
                ]
            }
        }
        url = reverse('cards')
        response = self.client.post(url, data=card_post_json, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cards_get(self):
        """
        Ensure we can get all cards object.
        """
        url = reverse('cards')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual( response.data["cards"]["count"], 2)

    def test_latest_card_data(self):
        """Ensure we only get the latest version for the card"""

        url = reverse('cards')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cards"]["results"][0]["card_data"]["id"], 2)
        self.assertEqual(response.data["cards"]["results"][1]["card_data"]["id"], 3)