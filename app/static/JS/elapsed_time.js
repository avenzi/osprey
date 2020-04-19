/**
 * @fileoverview This file is used in parts of this web application that need a timer,
 * such as the livefeed page
 */

/**
 * A timer that displays hours, minutes, seconds, and milliseconds since it was started
 */
class ElapsedTime {

    /**
     * @param {*} elem The HTML element to be updated
     */
    constructor(elem) {
        // Time displayed in the HTML element
        this.time = 0;
        // Change between the last time taken and the current time
        this.offset;
        // Interval on which the update function is used
        this.interval;
        // Status of the timer
        this.isOn = false;
        // HTML element to be updated
        this.elem = elem;
    }

    /**
     * Updates the HTML element with the new time
     * @return {undefined}
     */
    update() {
        if (this.isOn) {
            this.time += this.delta();
        }
        this.elem.textContent = this.timeFormatter(this.time);
    }

    /**
     * Gets the change between the last time taken and the current time
     * @return {number} The change between the last time taken and the current time
     */
    delta() {
        var now = Date.now();
        var timePassed = now - this.offset;
        this.offset = now;
        return timePassed;
    }

    /**
     * Formats the time into a user friendly format
     * @param {number} time The time to be formatted
     * @return {string} The formatted time
     */
    timeFormatter(time) {
        time = new Date(time);

        var hours = time.getUTCHours().toString();
        var minutes = time.getUTCMinutes().toString();
        var seconds = time.getUTCSeconds().toString();
        var milliseconds = time.getUTCMilliseconds().toString();

        if (hours.length < 2) {
            hours = "0" + hours;
        }
        if (minutes.length < 2) {
            minutes = "0" + minutes;
        }
        if (seconds.length < 2) {
            seconds = "0" + seconds;
        }
        while (milliseconds.length < 3) {
            milliseconds = "0" + milliseconds;
        }
        
        return hours + ":" + minutes + ":" + seconds + "." + milliseconds;
    }
    
    /**
     * Starts the timer and updates the HTML element every millisecond
     * @return {undefined}
     */
    start() {
        this.interval = setInterval(this.update.bind(this), 10);
        this.offset = Date.now();
        this.isOn = true;
    }
}