import { MediaUdp } from "@dank074/discord-video-stream";
export declare function playVideo(video: string | {
    [key: string]: {
        [key: string]: string[];
    };
}, udpConn: MediaUdp, season?: number, episode?: number): Promise<void>;
export declare function playVideoScheduled(video: string, udpConn: MediaUdp, duration: number): Promise<string>;
