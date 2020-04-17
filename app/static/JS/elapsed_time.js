class ElapsedTime {
    constructor(elem) {
        this.time = 0;
        this.offset;
        this.interval;
        this.isOn = false;
        this.elem = elem;
    }

    update() {
        if (this.isOn) {
            this.time += this.delta();
        }
        this.elem.textContent = this.timeFormatter(this.time);
    }

    delta() {
        var now = Date.now();
        var timePassed = now - this.offset;
        this.offset = now;
        return timePassed;
    }

    timeFormatter(time) {
        time = new Date(time);

        var hours = time.getUTCHours().toString();
        var minutes = time.getUTCMinutes().toString();
        var seconds = time.getUTCSeconds().toString();
        var milliseconds = time.getUTCMilliseconds().toString();

        if (hours.length < 2) {
            hours = '0' + hours;
        }

        if (minutes.length < 2) {
            minutes = '0' + minutes;
        }

        if (seconds.length < 2) {
            seconds = '0' + seconds;
        }

        while (milliseconds.length < 3) {
            milliseconds = '0' + milliseconds;
        }
        
        return hours + ':' + minutes + ':' + seconds + '.' + milliseconds;
    }
    
    start() {
        this.interval = setInterval(this.update.bind(this), 10);
        this.offset = Date.now();
        this.isOn = true;
    }
}