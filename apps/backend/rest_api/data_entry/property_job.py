from rest_api.models import Property
from rest_api.serializers import PropertySerializer


def find_or_create_property(
    name, datatype="value_varchar", querytype=None, description=None
):
    try:
        obj = Property.objects.get(name=name)
        created = False
    except Property.DoesNotExist:

        obj = PropertySerializer(
            data={
                "name": name,
                "datatype": datatype,
                "naquerytypeme": querytype,
                "description": description,
            }
        )
        if obj.is_valid():
            obj.save()
            # obj = Property.objects.create(name=name, datatype=datatype, querytype=querytype, description=description)
            created = True
        else:
            obj = None
            created = False
    except Exception as e:
        print(f"Error occurred: {e}")
        obj = None
        created = False
    return obj, created


def delete_property(name):
    try:
        count, _ = Property.objects.filter(name=name).delete()
        return count
    except Exception as e:
        print(f"Error occurred: {e}")
        return False
