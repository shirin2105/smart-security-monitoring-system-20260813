import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { EvidenceMedia } from './EvidenceMedia';

afterEach(() => vi.restoreAllMocks());

describe('EvidenceMedia', () => {
  it('giữ ngữ nghĩa ảnh cho artifact cũ', () => {
    render(
      <EvidenceMedia
        artifact={{ url: '/evidence.jpg', redactionStatus: 'COMPLETE' }}
        description="sự cố #1"
        className="preview"
      />,
    );

    expect(screen.getByAltText('Ảnh bằng chứng sự cố #1')).toBeDefined();
  });

  it('seek và dừng video tại evidence window', () => {
    const pause = vi
      .spyOn(HTMLMediaElement.prototype, 'pause')
      .mockImplementation(() => undefined);
    render(
      <EvidenceMedia
        artifact={{
          url: '/source.mp4',
          redactionStatus: 'COMPLETE',
          clipStartS: 47.75,
          clipEndS: 59.75,
        }}
        description="sự cố #2"
        className="preview"
      />,
    );

    const video = screen.getByLabelText('Video bằng chứng sự cố #2') as HTMLVideoElement;
    fireEvent.loadedMetadata(video);
    expect(video.currentTime).toBe(47.75);

    video.currentTime = 59.8;
    fireEvent.timeUpdate(video);
    expect(pause).toHaveBeenCalledOnce();
  });
});
