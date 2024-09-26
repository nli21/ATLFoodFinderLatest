
from django.utils.duration import duration_string
from django.views.generic import ListView
from django.views import View
from django.shortcuts import render, redirect
from .models import *
import googlemaps
from django.conf import settings
from .forms import *
from datetime import datetime

class HomeView(ListView):
    template_name = "project_content/geocoding.html"
    context_object_name = 'my_data'
    model = Locations
    success_url = "/"

class DistanceView(View):
    template_name = "project_content/distance.html"

    def get(self, request):
        form = DistanceForm()
        distances = Distances.objects.all()
        context = {
            'form': form,
            'distances': distances
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = DistanceForm(request.POST)
        if form.is_valid():
            from_location = form.cleaned_data['from_location']
            from_location_info = Locations.objects.get(name=from_location)
            from_address_string = (
                f"{from_location_info.address}, {from_location_info.zipcode}, "
                f"{from_location_info.city}, {from_location_info.country}"
            )

            to_location = form.cleaned_data['to_location']
            to_location_info = Locations.objects.get(name=to_location)
            to_address_string = (
                f"{to_location_info.address}, {to_location_info.zipcode}, "
                f"{to_location_info.city}, {to_location_info.country}"
            )

            mode = form.cleaned_data['mode']
            now = datetime.now()

            gmaps = googlemaps.Client(key=settings.GOOGLE_API_KEY)
            calculate = gmaps.distance_matrix(
                from_address_string,
                to_address_string,
                mode=mode,
                departure_time=now,
            )

            # Extract distance and duration details
            duration_seconds = calculate['rows'][0]['elements'][0]['duration']['value']
            duration_minutes = duration_seconds / 60
            distance_meters = calculate['rows'][0]['elements'][0]['distance']['value']
            distance_kilometers = distance_meters / 1000

            if 'duration_in_traffic' in calculate['rows'][0]['elements'][0]:
                duration_in_traffic_seconds = calculate['rows'][0]['elements'][0]['duration_in_traffic']['value']
                duration_in_traffic_minutes = duration_in_traffic_seconds / 60
            else:
                duration_in_traffic_minutes = None

            # Save the distance calculation in the database
            obj = Distances(
                from_location=from_location_info,
                to_location=to_location_info,
                mode=mode,
                distance_km=distance_kilometers,
                duration_minutes=duration_minutes,
                duration_traffic_mins=duration_in_traffic_minutes
            )
            obj.save()

        else:
            print(form.errors)

        return redirect('my_distance_view')

class GeocodingView(View):
    template_name = "project_content/geocoding.html"

    def get(self, request, pk):
        location = Locations.objects.get(pk=pk)

        if location.lng and location.lat and location.place_id is not None:
            lat = location.lat
            lng = location.lng
            place_id = location.place_id
            label = "from my database"

        elif location.address and location.country and location.zipcode and location.city is not None:
            address_string = (
                f"{location.address}, {location.zipcode}, {location.city}, {location.country}"
            )
            gmaps = googlemaps.Client(key=settings.GOOGLE_API_KEY)
            result = gmaps.geocode(address_string)[0]

            lat = result.get('geometry', {}).get('location', {}).get('lat', None)
            lng = result.get('geometry', {}).get('location', {}).get('lng', None)
            place_id = result.get('place_id', {})
            label = "from my API call"

            location.lat = lat
            location.lng = lng
            location.place_id = place_id
            location.save()

        else:
            lat = lng = place_id = label = ""

        context = {
            'location': location,
            'lat': lat,
            'lng': lng,
            'place_id': place_id,
            'label': label
        }
        return render(request, self.template_name, context)
