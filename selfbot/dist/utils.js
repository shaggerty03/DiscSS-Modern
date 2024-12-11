import { getInputMetadata, inputHasAudio, streamLivestreamVideo } from "@dank074/discord-video-stream";
export async function playVideo(video, udpConn, season, episode) {
    if (typeof video === 'object') {
        for (const show in video) {
            if (season && episode) {
                const seasonKey = `Season ${season.toString().padStart(2, '0')}`;
                if (seasonKey in video[show]) {
                    const episodes = video[show][seasonKey];
                    if (episode <= episodes.length) {
                        const episodePath = episodes[episode - 1];
                        let includeAudio = true;
                        try {
                            const metadata = await getInputMetadata(episodePath);
                            includeAudio = inputHasAudio(metadata);
                        }
                        catch (e) {
                            console.log(e);
                            return;
                        }
                        console.log("Started playing video...");
                        udpConn.mediaConnection.setSpeaking(true);
                        udpConn.mediaConnection.setVideoStatus(true);
                        try {
                            const res = await streamLivestreamVideo(episodePath, udpConn, includeAudio);
                            console.log("Finished playing video " + res);
                        }
                        catch (e) {
                            console.log(e);
                        }
                        finally {
                            udpConn.mediaConnection.setSpeaking(false);
                            udpConn.mediaConnection.setVideoStatus(false);
                        }
                        // Play the rest of the episodes
                        for (let i = episode; i < episodes.length; i++) {
                            const nextEpisodePath = episodes[i];
                            let includeAudio = true;
                            try {
                                const metadata = await getInputMetadata(nextEpisodePath);
                                includeAudio = inputHasAudio(metadata);
                            }
                            catch (e) {
                                console.log(e);
                                return;
                            }
                            console.log("Started playing video...");
                            udpConn.mediaConnection.setSpeaking(true);
                            udpConn.mediaConnection.setVideoStatus(true);
                            try {
                                const res = await streamLivestreamVideo(nextEpisodePath, udpConn, includeAudio);
                                console.log("Finished playing video " + res);
                            }
                            catch (e) {
                                console.log(e);
                            }
                            finally {
                                udpConn.mediaConnection.setSpeaking(false);
                                udpConn.mediaConnection.setVideoStatus(false);
                            }
                        }
                    }
                }
            }
            else {
                for (const season in video[show]) {
                    for (const episode of video[show][season]) {
                        let includeAudio = true;
                        try {
                            const metadata = await getInputMetadata(episode);
                            includeAudio = inputHasAudio(metadata);
                        }
                        catch (e) {
                            console.log(e);
                            return;
                        }
                        console.log("Started playing video...");
                        udpConn.mediaConnection.setSpeaking(true);
                        udpConn.mediaConnection.setVideoStatus(true);
                        try {
                            const res = await streamLivestreamVideo(episode, udpConn, includeAudio);
                            console.log("Finished playing video " + res);
                        }
                        catch (e) {
                            console.log(e);
                        }
                        finally {
                            udpConn.mediaConnection.setSpeaking(false);
                            udpConn.mediaConnection.setVideoStatus(false);
                        }
                    }
                }
            }
        }
    }
    else {
        let includeAudio = true;
        try {
            const metadata = await getInputMetadata(video);
            includeAudio = inputHasAudio(metadata);
        }
        catch (e) {
            console.log("Error getting metadata:", e);
            return;
        }
        console.log("Started playing video...");
        udpConn.mediaConnection.setSpeaking(true);
        udpConn.mediaConnection.setVideoStatus(true);
        try {
            const res = await streamLivestreamVideo(video, udpConn, includeAudio);
            console.log("Finished playing video " + res);
        }
        catch (e) {
            console.log(e);
        }
        finally {
            udpConn.mediaConnection.setSpeaking(false);
            udpConn.mediaConnection.setVideoStatus(false);
        }
    }
}
export async function playVideoScheduled(video, udpConn, duration) {
    let includeAudio = true;
    try {
        const metadata = await getInputMetadata(video);
        includeAudio = inputHasAudio(metadata);
    }
    catch (e) {
        console.log(e);
        return "Error";
    }
    console.log("Started playing video...");
    udpConn.mediaConnection.setSpeaking(true);
    udpConn.mediaConnection.setVideoStatus(true);
    try {
        console.log(`Playing video for ${duration} seconds...`);
        const res = await streamLivestreamVideo(video, udpConn, includeAudio);
        console.log("Finished playing video " + res);
        return "Playing";
    }
    catch (e) {
        console.log(e);
        return "Error";
    }
    finally {
        udpConn.mediaConnection.setSpeaking(false);
        udpConn.mediaConnection.setVideoStatus(false);
    }
}
