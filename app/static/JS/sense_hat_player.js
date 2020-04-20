class SenseHatPlayer {
    constructor(session_id, sensor_id) {
        this.sensor_id = sensor_id;
        this.session_id = session_id;

        this.slider = document.getElementById('playback-slider');
        this.temperature = document.getElementById(`sense-temperature-${this.sensor_id}`);
        this.pressure = document.getElementById(`sense-pressure-${this.sensor_id}`);
        this.humidity = document.getElementById(`sense-humidity-${this.sensor_id}`);

        this.last_fetched_time = 0;
        this.fetching = false;

        this._buffer_interval();
    }

    _buffer_interval() {
        var that = this;
        window.setInterval(function() {
            var current_playback_time = parseInt(that.slider.value);
            if (!that.fetching && Math.abs(current_playback_time - that.last_fetched_time) > 800) {
                that.last_fetched_time = current_playback_time;
                that.fetching = true;
                that.fetch(current_playback_time);
            }
        }, 400);
    }

    fetch(time) {
        var that = this;

        $.get(`/retrieve_sense/${time}/4/${this.session_id}/${this.sensor_id}`, function(data) {
            if (data['temperature'] !== undefined) {
                that.receive_data(data);
            } else {
                that.receive_data({
                    'temperature': '--.-',
                    'pressure': '--.-',
                    'humidity': '--.-',
                });
            }
        }).always(function() {
            that.fetching = false;
        });
    }

    receive_data(data) {
        this.temperature.innerHTML = data['temperature'];
        this.pressure.innerHTML = data['pressure'];
        this.humidity.innerHTML = data['humidity'];
    }

}