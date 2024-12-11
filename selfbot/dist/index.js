import { Client, StageChannel } from "discord.js-selfbot-v13";
import { Streamer, Utils, NewApi } from "@dank074/discord-video-stream";
import { globals } from "./globals.js";
import express from 'express';
import config from './config.json' with { type: "json" };
import fs from 'node:fs';
import { spawn } from 'node:child_process';
import { promisify } from 'node:util';
const sleep = promisify(setTimeout);
const streamer = new Streamer(new Client());
const app = express();
let current;
app.use(express.json());
streamer.client.on("ready", () => {
    console.log(`Logged in as ${streamer.client.user.tag}`);
});
app.get('/status', async (req, res) => {
    try {
        const channel = await streamer.client.channels.fetch("1270611781441683456");
        if (!channel.isText())
            return res.sendStatus(400);
        const response = {
            status: 'OK',
            message: 'Server is running',
        };
        await channel.send(`STATUS: ${JSON.stringify(response)}`);
        res.setHeader('Content-Type', 'application/json');
        res.status(200).json(response);
    }
    catch (error) {
        console.error(error);
        res.sendStatus(500);
    }
});
const getVideoDetails = async (videoFile) => {
    const command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,width,height", "-of", "json", videoFile];
    const process = spawn(command[0], command.slice(1));
    let output = '';
    process.stdout.on('data', (data) => {
        output += data.toString();
    });
    process.stderr.on('data', (data) => {
        console.error(`stderr: ${data}`);
    });
    return new Promise((resolve, reject) => {
        process.on('close', (code) => {
            if (code === 0) {
                const jsonOutput = JSON.parse(output);
                const frameRate = jsonOutput.streams[0].r_frame_rate;
                const [numerator, denominator] = frameRate.split('/').map(Number);
                const fps = numerator / denominator;
                const width = parseInt(jsonOutput.streams[0].width);
                const height = parseInt(jsonOutput.streams[0].height);
                resolve({ fps, width, height });
            }
            else {
                console.error(`process exited with code ${code}`);
                reject(code);
            }
        });
    });
};
app.post('/play', async (req, res) => {
    try {
        if (current) {
            res.status(400).json({ status: 'ERROR', message: 'Already playing media' });
            return;
        }
        const { title, path, sorted_episodes = {}, guild_id, type, author, season, episode } = req.body;
        const channell = await streamer.client.channels.fetch("1270611781441683456");
        if (!channell.isText())
            return res.sendStatus(400);
        await channell.send(`Play: ${title}\nPath: ${path}\nSorted Episodes: ${sorted_episodes}\nAuthor: ${author}\nGuild ID: ${guild_id}\nType: ${type}\nSeason: ${season}\nEpisode: ${episode}`);
        if (!title || !path || !author || !guild_id) {
            return res.status(400).json({ status: 'ERROR', message: 'Missing required fields' });
        }
        const guild = await streamer.client.guilds.fetch(guild_id);
        const member = await guild.members.fetch(author);
        if (!member) {
            return res.status(400).json({ status: 'ERROR', message: `Author not found (author: ${author})` });
        }
        const channel = member.voice.channel;
        if (!channel) {
            return res.status(400).json({ status: 'ERROR', message: 'User is not in a voice channel' });
        }
        await streamer.joinVoice(guild.id, channel.id);
        if (channel instanceof StageChannel) {
            await streamer.client.user.voice.setSuppressed(false);
        }
        const videoDetails = await getVideoDetails(path);
        const finalFps = videoDetails.fps > 0 ? videoDetails.fps : config.streamOpts.fps;
        let finalWidth = videoDetails.width > 0 ? videoDetails.width : config.streamOpts.width;
        let finalHeight = videoDetails.height > 0 ? videoDetails.height : config.streamOpts.height;
        if (finalWidth >= 3840 || finalHeight >= 2160) {
            finalWidth = 2560;
            finalHeight = 1440;
        }
        else if (finalWidth >= 2560 || finalHeight >= 1440) {
            finalWidth = 1920;
            finalHeight = 1080;
        }
        const { command, output } = NewApi.prepareStream(path, {
            width: finalWidth,
            height: finalHeight,
            frameRate: config.streamOpts.fps,
            bitrateVideo: config.streamOpts.bitrateKbps,
            bitrateVideoMax: config.streamOpts.maxBitrateKbps,
            hardwareAcceleratedDecoding: config.streamOpts.hardware_acceleration,
            videoCodec: Utils.normalizeVideoCodec(config.streamOpts.videoCodec)
        });
        console.log('Command details:', JSON.stringify(Object.getOwnPropertyDescriptors(command), null, 2));
        console.log('Output:', JSON.stringify(output, null, 2));
        current = command;
        try {
            await NewApi.playStream(output, streamer, {
                forceChacha20Encryption: true
            }).catch(async (err) => {
                console.error("Error in playStream:", err);
            });
            res.status(200).json({
                status: 'OK',
                message: `Playing media (FPS: ${finalFps}, Width: ${finalWidth}, Height: ${finalHeight}, Path: ${path})`
            });
        }
        catch (error) {
            console.error(`Error playing media: ${error}`);
            res.status(500).json({ status: 'ERROR', message: 'Failed to play media' });
        }
    }
    catch (error) {
        console.error(`Error in play: ${error}`);
        res.sendStatus(500);
    }
});
app.post('/play-scheduled', async (req, res) => {
    try {
        if (current) {
            res.status(400).json({ status: 'ERROR', message: 'Already playing media' });
            return;
        }
        const { title, path, guild_id, type, author, duration, movie_duration } = req.body;
        if (!title || !path || !guild_id || !type || !author || !duration) {
            return res.status(400).json({ status: 'ERROR', message: 'Missing required fields' });
        }
        const numStreams = Math.ceil(duration / movie_duration);
        const totalPlayTime = numStreams * movie_duration;
        console.log(`Number of streams: ${numStreams}, Total play time: ${totalPlayTime}`);
        const guild = await streamer.client.guilds.fetch(guild_id);
        const member = await guild.members.fetch(author);
        const channel = member.voice.channel;
        if (!channel) {
            return res.status(400).json({ status: 'ERROR', message: 'User is not in a voice channel' });
        }
        await streamer.joinVoice(guild.id, channel.id);
        if (channel instanceof StageChannel) {
            await streamer.client.user.voice.setSuppressed(false);
        }
        const videoDetails = await getVideoDetails(path);
        const finalFps = videoDetails.fps > 0 ? videoDetails.fps : config.streamOpts.fps;
        let finalWidth = videoDetails.width > 0 ? videoDetails.width : config.streamOpts.width;
        let finalHeight = videoDetails.height > 0 ? videoDetails.height : config.streamOpts.height;
        if (finalWidth >= 3840 || finalHeight >= 2160) {
            finalWidth = 2560;
            finalHeight = 1440;
        }
        else if (finalWidth >= 2560 || finalHeight >= 1440) {
            finalWidth = 1920;
            finalHeight = 1080;
        }
        globals.startTime = Date.now();
        globals.duration = totalPlayTime;
        const { command, output } = NewApi.prepareStream(path, {
            width: finalWidth,
            height: finalHeight,
            frameRate: finalFps,
            bitrateVideo: config.streamOpts.bitrateKbps,
            bitrateVideoMax: config.streamOpts.maxBitrateKbps,
            hardwareAcceleratedDecoding: config.streamOpts.hardware_acceleration,
            videoCodec: Utils.normalizeVideoCodec(config.streamOpts.videoCodec)
        });
        current = command;
        res.status(200).json({
            status: 'OK',
            message: `Playing scheduled media (Title: ${title}, Duration: ${duration})`
        });
        const endTime = globals.startTime + (totalPlayTime * 1000);
        while (Date.now() < endTime) {
            try {
                await NewApi.playStream(output, streamer)
                    .catch(() => current?.kill("SIGTERM"));
                let streamCount = 1;
                const streamCountFile = 'streamCount.txt';
                if (fs.existsSync(streamCountFile)) {
                    const count = fs.readFileSync(streamCountFile, 'utf8');
                    streamCount = parseInt(count) + 1;
                }
                fs.writeFileSync(streamCountFile, streamCount.toString());
                const channelToNotify = await streamer.client.channels.fetch("1272196628518014986");
                if (channelToNotify.isText()) {
                    await channelToNotify.send(`Streaming for the ${streamCount}th time. Streaming ${title} again in 15 minutes..`);
                }
                current?.kill("SIGTERM");
                await new Promise(resolve => setTimeout(resolve, 900000)); // 15 minutes wait
                if (Date.now() < endTime) {
                    await streamer.joinVoice(guild.id, channel.id);
                    if (channel instanceof StageChannel) {
                        await streamer.client.user.voice.setSuppressed(false);
                    }
                }
            }
            catch (error) {
                console.error(error);
                break;
            }
        }
        current?.kill("SIGTERM");
        streamer.leaveVoice();
    }
    catch (error) {
        console.error(error);
        current?.kill("SIGTERM");
        res.sendStatus(500);
    }
});
app.get('/timeleft', async (req, res) => {
    try {
        if (current) {
            const elapsedTime = (Date.now() - globals.startTime) / 1000;
            const timeLeft = globals.duration - elapsedTime;
            res.status(200).json({ status: 'OK', message: `${timeLeft}` });
        }
        else {
            res.status(400).json({ status: 'ERROR', message: 'No stream to get time left' });
        }
    }
    catch (error) {
        console.error(error);
        res.sendStatus(500);
    }
});
app.get('/pause', async (req, res) => {
    try {
        if (current) {
            current.kill("SIGSTOP");
            res.status(200).json({ status: 'OK', message: 'Paused movie' });
        }
        else {
            res.status(400).json({ status: 'ERROR', message: 'No stream to pause' });
        }
    }
    catch (error) {
        console.error(error);
        res.sendStatus(500);
    }
});
app.get('/resume', async (req, res) => {
    try {
        if (current) {
            current.kill("SIGCONT");
            res.status(200).json({ status: 'OK', message: 'Resumed movie' });
        }
        else {
            res.status(400).json({ status: 'ERROR', message: 'No stream to resume' });
        }
    }
    catch (error) {
        console.error(error);
        res.sendStatus(500);
    }
});
app.get('/stop', async (req, res) => {
    try {
        if (current) {
            try {
                streamer.leaveVoice();
                current?.kill("SIGTERM");
            }
            catch (e) {
                console.error("Error during voice disconnect:", e);
            }
            res.status(200).json({ status: 'OK', message: 'Stopped movie' });
        }
        else {
            res.status(400).json({ status: 'ERROR', message: 'No stream to stop' });
        }
    }
    catch (error) {
        console.error(error);
        res.status(500).json({ status: 'ERROR', message: 'Error stopping stream' });
    }
});
app.get('/disconnect', async (req, res) => {
    try {
        if (current) {
            try {
                current?.kill("SIGTERM");
                streamer.leaveVoice();
            }
            catch (e) {
                console.error("Error during voice disconnect:", e);
            }
            res.status(200).json({ status: 'OK', message: 'Disconnected from voice channel' });
        }
        else {
            res.status(400).json({ status: 'ERROR', message: 'Not connected to a voice channel' });
        }
    }
    catch (error) {
        console.error(error);
        res.status(500).json({ status: 'ERROR', message: 'Error disconnecting' });
    }
});
app.listen(3000, () => {
    console.log('Server is running on port 3000');
});
streamer.client.login(config.token);
