import React, { Component } from 'react';
import { withGoogleMap, GoogleMap, Marker, InfoWindow } from "react-google-maps";

// Map component
// <script src="https://maps.googleapis.com/maps/api/js"></script>

const ProblemMap = withGoogleMap(props => (
  <GoogleMap
    defaultZoom={props.zoom}
    defaultCenter={{ lat: props.lat, lng: props.lng }}
    defaultOptions={{ streetViewControl: false, scrollwheel: false }}
  >
    {props.markers.map((marker, key) => (
      <Marker {...marker}
              key={key}
              onClick={() => props.onMarkerClick(marker)}
      >
        {marker.showInfo && (
          <InfoWindow onCloseClick={() => props.onMarkerClose(marker)}>
            <div>{marker.info}</div>
          </InfoWindow>
        )}
      </Marker>
    ))}
  </GoogleMap>
));

export default class Map extends Component {
  state = {
    markers: []
  }

  handleMarkerClick = this.handleMarkerClick.bind(this);
  handleMarkerClose = this.handleMarkerClose.bind(this);

  handleMarkerClick(targetMarker) {
    this.setState({
      markers: this.state.markers.map(marker => {
        if (marker === targetMarker) {
          return {
            ...marker,
            showInfo: true,
          };
        }
        return marker;
      }),
    });
  }

  handleMarkerClose(targetMarker) {
    this.setState({
      markers: this.state.markers.map(marker => {
        if (marker === targetMarker) {
          return {
            ...marker,
            showInfo: false,
          };
        }
        return marker;
      }),
    });
  }

  getMarkerIcon(pinColor = "FE7569") {
    let pinImage = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|" + pinColor,
      new google.maps.Size(21, 34),
      new google.maps.Point(0,0),
      new google.maps.Point(10, 34)
    );
    return pinImage;
  }

  getMarkerShadow() {
    let pinShadow = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_shadow",
      new google.maps.Size(40, 37),
      new google.maps.Point(0, 0),
      new google.maps.Point(12, 35)
    );
    return pinShadow;
  }

  componentWillReceiveProps(nextProps) {
    this.setState({
      markers: []
    });
  }

  render() {
    const { items, actions, loading, descriptions } = this.props;
    let entities_class = "entities";
    entities_class = loading ? entities_class + " ex-state-loading" : entities_class;

    const geo_items = items.filter(item => !!(item.extra && item.extra.geoposition))

    let min_lng = null,
        min_lat = null,
        max_lng = null,
        max_lat = null,
        markers = this.state.markers,
        shadow = this.getMarkerShadow();

    for (const item of geo_items) {
      const coords = item.extra.geoposition.split(','),
            lng = parseFloat(coords[1]),
            lat = parseFloat(coords[0]);
      min_lng = min_lng != null && min_lng < lng ? min_lng : lng;
      max_lng = max_lng != null && max_lng > lng ? max_lng : lng;
      min_lat = min_lat != null && min_lat < lat ? min_lat : lat;
      max_lat = max_lat != null && max_lat > lat ? max_lat : lat;

      let pinColor = "FE7569";
      if (item.short_marks.length && item.short_marks[0].view_class.length) {
        for (const cl of item.short_marks[0].view_class) {
          if(cl.startsWith("pin-color-")) {
            pinColor = cl.replace("pin-color-", "").toUpperCase();
          }
        }
      }

      const info = (
        <div>
          <h4>{item.entity_name}</h4>
          <ul className="ex-attrs">
            {item.short_characteristics.map(
              (child, i) =>
                <li data-path={child.path} key={i}
                    data-view-class={child.view_class.join(" ")}>
                  <strong>{child.name}:</strong>&nbsp;
                  {child.values.join("; ")}
                </li>
            )}
          </ul>
        </div>
      );

      markers.push(
        {
          position: {lat: lat, lng: lng},
          info: info,
          icon: this.getMarkerIcon(pinColor),
          shadow: shadow
        }
      );
    }


    const GLOBE_WIDTH = 256, // a constant in Google's map projection
          west = min_lng,
          east = max_lng;
    let angle = east - west;
    if (angle < 0) {
      angle += 360;
    }
    const pixelWidth = 320;
    const zoom = Math.round(Math.log(pixelWidth * 360 / angle / GLOBE_WIDTH) / Math.LN2);

    const map_lng = min_lng + (max_lng - min_lng) / 2,
          map_lat = min_lat + (max_lat - min_lat) / 2;

    return (
      <div className={entities_class}>
        <ProblemMap markers={markers}
                    lng={map_lng}
                    lat={map_lat}
                    zoom={zoom}
                    containerElement={
                      <div style={{ height: '400px' }} />
                    }
                    mapElement={
                      <div style={{ height: '400px' }} />
                    }
                    onMarkerClick={this.handleMarkerClick}
                    onMarkerClose={this.handleMarkerClose}
        />
      </div>
    );
  }
}
