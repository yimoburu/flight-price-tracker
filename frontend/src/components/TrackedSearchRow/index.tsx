import { useState } from 'react';
import type { TrackedSearch, PriceHistory } from '../../types/tracking';
import { deleteTrackedSearch, getPriceHistory } from '../../api/tracking';
import { PriceHistoryChart } from '../PriceHistoryChart';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { ChevronDown, ChevronUp, TrendingDown } from 'lucide-react';

interface TrackedSearchRowProps {
  search: TrackedSearch;
  onDeleted: (id: string) => void;
}

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return 'Never';
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffHours = Math.floor(diffMs / 3600000);
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

export function TrackedSearchRow({ search, onDeleted }: TrackedSearchRowProps) {
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<PriceHistory | null>(null);
  const [historyStatus, setHistoryStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  async function handleConfirmDelete() {
    setDeleteDialogOpen(false);
    try {
      await deleteTrackedSearch(search.id);
      onDeleted(search.id);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Delete failed');
    }
  }

  async function toggleHistory() {
    const nowOpen = !historyOpen;
    setHistoryOpen(nowOpen);
    if (nowOpen && history === null) {
      setHistoryStatus('loading');
      try {
        const h = await getPriceHistory(search.id);
        setHistory(h);
        setHistoryStatus('idle');
      } catch {
        setHistoryStatus('error');
      }
    }
  }

  const threshold = parseFloat(search.threshold_price);
  const bestPrice = search.current_best_price ? parseFloat(search.current_best_price) : null;
  const bestBelowThreshold = bestPrice !== null && bestPrice < threshold;

  return (
    <Card className="mb-4">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xl font-semibold">{search.origin} → {search.destination}</span>
              <Badge variant="secondary">{search.trip_type === 'one_way' ? 'One Way' : 'Round Trip'}</Badge>
              {bestBelowThreshold && <TrendingDown className="h-4 w-4 text-green-600" />}
            </div>
            <div className="text-sm text-neutral-500 mt-1">
              {search.departure_date_from} – {search.departure_date_to}
              {search.trip_type === 'round_trip' && search.return_date_from && (
                <span> · Return {search.return_date_from} – {search.return_date_to}</span>
              )}
            </div>
            <div className="flex gap-4 mt-2 text-sm">
              <span>Threshold: <span className="font-medium">USD {parseFloat(search.threshold_price).toFixed(2)}</span></span>
              {bestPrice !== null ? (
                <span>Best: <span className={`font-medium ${bestBelowThreshold ? 'text-green-600' : 'text-neutral-900'}`}>
                  USD {bestPrice.toFixed(2)}
                </span></span>
              ) : (
                <span data-testid="best-price">–</span>
              )}
            </div>
            <div className="text-xs text-neutral-400 mt-1" data-testid="last-checked">
              Last checked: <span>{formatRelativeTime(search.last_checked_at ?? null)}</span>
            </div>
          </div>
          <div className="flex flex-col gap-2 flex-shrink-0">
            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="text-red-600 hover:text-red-700 border-red-200">
                  Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete tracked search?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will stop tracking prices for {search.origin} → {search.destination}. This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleConfirmDelete} className="bg-red-600 hover:bg-red-700">Delete</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleHistory}
              aria-expanded={historyOpen}
              className="text-xs text-neutral-500"
            >
              {historyOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              History
            </Button>
          </div>
        </div>
        {deleteError && <p className="text-sm text-red-500 mt-2" role="alert">{deleteError}</p>}
        {historyOpen && (
          <div className="mt-4 border-t pt-4">
            {historyStatus === 'loading' && <p>Loading history...</p>}
            {historyStatus === 'error' && <p>Failed to load history.</p>}
            {historyStatus === 'idle' && history && (
              <PriceHistoryChart snapshots={history.snapshots} />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
