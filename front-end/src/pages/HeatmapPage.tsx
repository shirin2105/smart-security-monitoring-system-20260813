import { Map as MapIcon } from 'lucide-react';

import { EmptyState } from '../components/common/States';

/**
 * BAC-55 — tính năng nâng cao, theo PLANNING chỉ mở khi toàn bộ P0 đã xanh
 * (hạn 20–21/08) và phụ thuộc API tổng hợp BAC-48 của Backend.
 *
 * Giữ route sẵn để điều hướng và phân quyền đã kiểm chứng được từ bây giờ.
 */
export function HeatmapPage() {
  return (
    <div className="flex flex-1 flex-col p-4 md:p-6">
      <header className="mb-4 flex items-center gap-2">
        <MapIcon className="h-5 w-5 text-blue-400" aria-hidden />
        <h1 className="text-base font-bold tracking-wide text-white">
          BẢN ĐỒ ĐIỂM NÓNG AN NINH
        </h1>
      </header>

      <section className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-gray-800 bg-gray-900/40">
        <EmptyState
          icon={<MapIcon className="h-10 w-10" />}
          title="Tính năng chưa mở"
          hint="Heatmap (BAC-55) chỉ được triển khai sau khi toàn bộ hạng mục P0 đạt yêu cầu, và cần API tổng hợp BAC-48 từ backend."
        />
      </section>
    </div>
  );
}
