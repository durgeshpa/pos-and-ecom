from cms.exceptions import NotAllowed
import logging

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
CMS_DESIGNER_GROUP="designer"
CMS_REVIEWER_GROUP="reviewer"

def check_group_designer(user):
	return user.groups.filter(name=CMS_DESIGNER_GROUP).exists()


def check_group_reviewer(user):
	return user.groups.filter(name=CMS_REVIEWER_GROUP).exists()



def has_cards_create_permission(user):
	if(not check_group_designer(user)):
		info_logger.info(f"{user.phone_number} not authorized to create cms cards")
		raise NotAllowed()
	return True

def has_apps_create_permission(user):
	if(not check_group_designer(user)):
		info_logger.info(f"{user.phone_number} not authorized to create cms apps")
		raise NotAllowed()
	return True

def has_apps_status_change_permission(user):
	if(not check_group_reviewer(user)):
		info_logger.info(f"{user.phone_number} not authorized to change status of cms apps")
		raise NotAllowed()
	return True


def has_pages_create_permission(user):
	if(not check_group_designer(user)):
		info_logger.info(f"{user.phone_number} not authorized to create cms pages")
		raise NotAllowed()
	return True


def has_pages_status_change_permission(user):
	if(not check_group_reviewer(user)):
		info_logger.info(f"{user.phone_number} not authorized to change status of pages")
		raise NotAllowed()
	return True
