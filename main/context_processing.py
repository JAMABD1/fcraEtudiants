from main.models import Profile
from django.contrib.auth.models import User

def takeinfoUser(response):
      
     cureentuser=response.user
     
     try:
        user_id=cureentuser.id
        profile=list(Profile.objects.filter(user_id=user_id).values())
        username=User.objects.get(id=user_id)
        return {"profile":profile,"username":username}
     except:
         return False


def default(response):
    userprofile=takeinfoUser(response)
    if userprofile is False:
        return {}
    username=userprofile["username"]
    profileuser=userprofile["profile"]
 
    return {
 "username":username,"profileuser":profileuser
    }