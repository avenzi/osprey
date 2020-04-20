class MP3Degapper {
    SECONDS_PER_SAMPLE = 1 / 44100;

    // Since most MP3 encoders store the gapless metadata in binary, we'll need a
    // method for turning bytes into integers.  Note: This doesn't work for values
    // larger than 2^30 since we'll overflow the signed integer type when shifting.
   read_int(buffer) {
        var result = buffer.charCodeAt(0);
        for (var i = 1; i < buffer.length; ++i) {
            result <<= 8;
            result += buffer.charCodeAt(i);
        }
        return result;
    }

    degap_buffer(arrayBuffer) {
        // Gapless data is generally within the first 512 bytes, so limit parsing.
        var byteStr = new TextDecoder().decode(arrayBuffer.slice(0, 512));

        var frontPadding = 0, endPadding = 0, realSamples = 0;

        var iTunesDataIndex = byteStr.indexOf('iTunSMPB');
        if (iTunesDataIndex != -1) {
            var frontPaddingIndex = iTunesDataIndex + 34;
            frontPadding = parseInt(byteStr.substr(frontPaddingIndex, 8), 16);

            var endPaddingIndex = frontPaddingIndex + 9;
            endPadding = parseInt(byteStr.substr(endPaddingIndex, 8), 16);

            var sampleCountIndex = endPaddingIndex + 9;
            realSamples = parseInt(byteStr.substr(sampleCountIndex, 16), 16);
        }


        var xingDataIndex = byteStr.indexOf('Xing');
        if (xingDataIndex == -1) xingDataIndex = byteStr.indexOf('Info');
        if (xingDataIndex != -1) {
            // parsing the Xing
            var frameCountIndex = xingDataIndex + 8;
            var frameCount = this.read_int(byteStr.substr(frameCountIndex, 4));

            // For Layer3 Version 1 and Layer2 there are 1152 samples per frame.
            var paddedSamples = frameCount * 1152;

            xingDataIndex = byteStr.indexOf('LAME');
            if (xingDataIndex == -1) xingDataIndex = byteStr.indexOf('Lavf');
            if (xingDataIndex != -1) {
            // See http://gabriel.mp3-tech.org/mp3infotag.html#delays for details of
            // how this information is encoded and parsed.
            var gaplessDataIndex = xingDataIndex + 21;
            var gaplessBits = this.read_int(byteStr.substr(gaplessDataIndex, 3));

            // Upper 12 bits are the front padding, lower are the end padding.
            frontPadding = gaplessBits >> 12;
            endPadding = gaplessBits & 0xFFF;
            }

            realSamples = paddedSamples - (frontPadding + endPadding);
        }

        return {
            audioDuration: realSamples * this.SECONDS_PER_SAMPLE,
            frontPaddingDuration: frontPadding * this.SECONDS_PER_SAMPLE
        };
    }
}