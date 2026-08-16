import { useRef } from 'react';

import { EventArtifact } from '../../domain/types';

interface EvidenceMediaProps {
  artifact: EventArtifact;
  description: string;
  className: string;
  autoPlay?: boolean;
  controls?: boolean;
}

const VIDEO_PATTERN = /\.(mp4|webm)(?:[?#].*)?$/i;

export function EvidenceMedia({
  artifact,
  description,
  className,
  autoPlay = false,
  controls = false,
}: EvidenceMediaProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  if (!VIDEO_PATTERN.test(artifact.url)) {
    return <img src={artifact.url} alt={`Ảnh bằng chứng ${description}`} className={className} />;
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
      video.pause();
    }
  };

  return (
    <video
      ref={videoRef}
      src={artifact.url}
      aria-label={`Video bằng chứng ${description}`}
      className={className}
      autoPlay={autoPlay}
      controls={controls}
      muted
      playsInline
      preload="metadata"
      onLoadedMetadata={seekToClipStart}
      onTimeUpdate={stopAtClipEnd}
    />
  );
}
