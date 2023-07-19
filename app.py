import pandas as pd
from datetime import datetime
#from joblib import load
import pickle
from sklearn.preprocessing import LabelEncoder

from flask import Flask, jsonify, render_template, request, redirect, url_for

app = Flask(__name__)
data = pd.read_csv("lstm_df.csv", low_memory=False)
#model_dep = pickle.load(open("model_dep.pkl",'rb'))  # Load the trained model
model_dep = pickle.load(open('model_duration.pkl','rb'))

@app.route('/')
def index():

    #origin = sorted(data['origin'].unique())
    origin_limit = 1000  # Set a limit for the number of origins to load initially
    unique_origins = sorted(data['origin'].unique()[:origin_limit])  # Fetch unique origins with a limit
    airline = sorted(data['airline'].unique())  # Fetch all unique airlines
    destination = sorted(data['destination'].unique())
    airline = sorted(data['airline'].unique())

    #data_json = data.to_json(orient='records')  # Convert data to JSON string
    
    return render_template('index.html', origin = unique_origins, destination=destination, airline=airline)  #date=date

@app.route('/load_destinations', methods=['POST'])
def load_destinations():
    selected_origin = request.form['origin']
    unique_destinations = sorted(data[data['origin'] == selected_origin]['destination'].unique())
    return jsonify(destinations=unique_destinations)



@app.route('/load_airlines', methods=['POST'])
def load_airlines():
    selected_origin = request.form['origin']
    selected_destination = request.form['destination']
    unique_airlines = sorted(
        data[(data['origin'] == selected_origin) & (data['destination'] == selected_destination)]['airline'].unique()
    )
    return jsonify(airlines=unique_airlines)



@app.route('/predict_departure', methods=['POST'])
def predict_departure():
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    airline = request.form.get('airline')
    date_str = request.form.get('date')


    # Convert the selected date to datetime format
    selected_date = datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d') # type: ignore

    print("Selected Criteria:")
    print("Origin:", origin)
    print("Destination:", destination)
    print("Airline:", airline)
    print("Date:", selected_date)

    # Filter the flight details based on the selected criteria
    filtered_data = data[(data['origin'] == origin) &
                         (data['destination'] == destination) &
                         (data['airline'] == airline) &
                         (data['ds'] == selected_date)
                        ]

    print("Filtered Data:")
    print(filtered_data)

    if filtered_data.empty:
        # No matching data found, return an error response
        return jsonify(msg='No matching data found for the selected criteria.')

    # Generate the input features for prediction
    input_features = filtered_data.drop(columns=['y_departure','y_arrival'])

    # Apply label encoding to categorical variables
    label_encoder = LabelEncoder()
    input_features['origin'] = label_encoder.fit_transform(input_features['origin'])
    input_features['destination'] = label_encoder.transform(input_features['destination'])
    input_features['airline'] = label_encoder.transform(input_features['airline'])

    # Predict the departure time using the trained model
    predicted_departure_time = model_dep.predict(input_features)

    # Format the predicted departure time
    formatted_departure_time = pd.to_datetime(predicted_departure_time, unit='m').strftime('%I:%M %p')
    print("formatted_departure_time is")

    # Return the predicted departure time as a response
    #return jsonify(predicted_departure_time=str(formatted_departure_time))
    return render_template('index.html', prediction_text='Departure Time: {}'.format(formatted_departure_time))

@app.route('/flight_details', methods=['POST'])
def flight_details():
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    airline = request.form.get('airline')

    # Filter the flight details based on the selected criteria
    filtered_data = data[(data['origin'] == origin) &
                         (data['destination'] == destination) &
                         (data['airline'] == airline)
                        ]

    # Convert departure and arrival time to the desired format
    filtered_data['y_departure'] = filtered_data['y_departure'].apply(lambda x: pd.to_datetime(x, unit='m').strftime('%I:%M %p'))
    filtered_data['y_arrival'] = filtered_data['y_arrival'].apply(lambda x: pd.to_datetime(x, unit='m').strftime('%I:%M %p'))

    
    # Calculate the difference between arrival and departure in minutes
    filtered_data['duration'] = (pd.to_datetime(filtered_data['y_arrival'], format='%I:%M %p')
                                 - pd.to_datetime(filtered_data['y_departure'], format='%I:%M %p')).dt.total_seconds() / 60

    # Remove data with duration less than or equal to 30 minutes
    filtered_data = filtered_data[filtered_data['duration'] >= 30]

    # Sort the filtered data by y_departure and y_arrival
    sorted_data = filtered_data.sort_values(by=['y_departure', 'y_arrival'])

    # Get the top 5 unique flight details based on y_departure and y_arrival
    unique_flights = sorted_data.drop_duplicates(subset=['y_departure', 'y_arrival'])

    #count = sum(lstm_df['y_departure'] > lstm_df['y_arrival']) #1066 # drop these

    # Extract the flight details including departure time, arrival time, and date
    flight_details = unique_flights[['flightNumber', 'airline', 'origin', 'destination', 'y_departure', 'y_arrival', 'ds']]

    # Convert the flight details to a list of dictionaries
    flight_details = flight_details.to_dict(orient='records')

    return render_template('flight_details.html', flight_details=flight_details, origin=origin, destination=destination, airline=airline)
     

if __name__== "__main__":
    app.run(debug=True)

