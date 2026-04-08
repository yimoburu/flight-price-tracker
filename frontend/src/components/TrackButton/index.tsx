import { useState } from 'react';
import { createTrackedSearch } from '../../api/tracking';
import type { SearchParams } from '../../types/flight';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Bell, BellRing } from 'lucide-react';

interface TrackButtonProps {
  searchParams: SearchParams;
  currency: string;
}

export function TrackButton({ searchParams, currency }: TrackButtonProps) {
  const [isTracking, setIsTracking] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [threshold, setThreshold] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleCancel() {
    setModalOpen(false);
    setEmail('');
    setThreshold('');
    setFormError(null);
    setSubmitting(false);
  }

  async function handleSave() {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setFormError('Please enter a valid email address');
      return;
    }
    if (!(parseFloat(threshold) > 0)) {
      setFormError('Please enter a price greater than 0');
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await createTrackedSearch({
        origin: searchParams.origin?.iata_code ?? '',
        destination: searchParams.destination?.iata_code ?? '',
        trip_type: searchParams.trip_type,
        departure_date_from: searchParams.departure_date_from,
        departure_date_to: searchParams.departure_date_to,
        return_date_from: searchParams.return_date_from || null,
        return_date_to: searchParams.return_date_to || null,
        adults: searchParams.adults,
        max_stops: searchParams.max_stops,
        threshold_price: parseFloat(threshold),
        alert_email: email,
      });
      setModalOpen(false);
      setIsTracking(true);
      setEmail('');
      setThreshold('');
      setFormError(null);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSubmitting(false);
    }
  }

  if (isTracking) {
    return (
      <Button disabled variant="outline" className="gap-2 text-neutral-400">
        <BellRing className="h-4 w-4" />Tracking
      </Button>
    );
  }

  return (
    <>
      <Button variant="outline" className="gap-2" onClick={() => setModalOpen(true)}>
        <Bell className="h-4 w-4" />Track this search
      </Button>
      <Dialog open={modalOpen} onOpenChange={(open) => { if (!open) handleCancel(); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Track this search</DialogTitle>
          </DialogHeader>
          {/* Route summary */}
          <div className="bg-sky-50 rounded-lg p-3 text-sm flex flex-col gap-1">
            <div className="font-medium">{searchParams.origin?.iata_code} → {searchParams.destination?.iata_code}</div>
            <Badge variant="secondary" className="w-fit">
              {searchParams.trip_type === 'one_way' ? 'One Way' : 'Round Trip'}
            </Badge>
            <div className="text-neutral-500">{searchParams.departure_date_from} to {searchParams.departure_date_to}</div>
          </div>
          {/* Email field */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="track-email">Alert email</Label>
            <Input
              id="track-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {/* Threshold field */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="track-threshold">Price threshold ({currency})</Label>
            <Input
              id="track-threshold"
              type="number"
              min="0.01"
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
          </div>
          {formError && <p role="alert" className="text-sm text-red-500">{formError}</p>}
          {/* Actions */}
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="ghost" onClick={handleCancel}>Cancel</Button>
            <Button onClick={handleSave} disabled={submitting}>Save</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
