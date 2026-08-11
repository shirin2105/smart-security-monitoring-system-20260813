import { useToastContext } from '../components/common/ToastProvider';

export function useToast() {
  const { toast, addToast, removeToast } = useToastContext();
  return { ...toast, addToast, removeToast };
}
