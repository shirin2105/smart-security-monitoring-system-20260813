import { useRef } from 'react';

import { EventArtifact } from '../../domain/types';

interface EvidenceMediaProps {
  artifact: EventArtifact;
  description: string;
  className?: string;
  style?: React.CSSProperties;
  autoPlay?: boolean;
  controls?: boolean;
  loop?: boolean;
}

const VIDEO_PATTERN = /\.(mp4|webm|mkv|mov)(?:[?#].*)?$/i;

export function EvidenceMedia({
  artifact,
  description,
  className,
  style,
  autoPlay = false,
  controls = false,
  loop = false,
}: EvidenceMediaProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  if (!artifact.url) return null;

  if (!VIDEO_PATTERN.test(artifact.url)) {
    return (
      <img
        src={artifact.url}
        alt={`Ảnh bằng chứng ${description}`}
        className={className}
        style={style}
        loading="lazy"
      />
    );
  }

  const seekToClipStart = () => {
    const video = videoRef.current;
    if (video && artifact.clipStartS != null) video.currentTime = artifact.clipStartS;
  };

  const stopAtClipEnd = () => {
    const video = videoRef.current;
    if (
      video &&
      artifact.clipEndS != null &&
      video.currentTime >= artifact.clipEndS
    ) {
      if (loop) {
        video.currentTime = artifact.clipStartS ?? 0;
      } else {
        video.pause();
      }
    }
  };

  return (
    <video
      ref={videoRef}
      src={artifact.url}
      aria-label={`Video bằng chứng ${description}`}
      className={className}
      style={style}
      autoPlay={autoPlay}
      controls={controls}
      loop={loop && artifact.clipEndS == null}
      muted
      playsInline
      preload="metadata"
      onLoadedMetadata={seekToClipStart}
      onTimeUpdate={stopAtClipEnd}
    />
  );
}

