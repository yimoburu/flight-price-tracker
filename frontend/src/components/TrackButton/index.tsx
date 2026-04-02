import { useState } from 'react';
import { createTrackedSearch } from '../../api/tracking';
import type { SearchParams } from '../../types/flight';

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

  if (isTracking) {
    return <button disabled>Tracking</button>;
  }

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

  return (
    <>
      <button onClick={() => setModalOpen(true)}>Track this search</button>
      {modalOpen && (
        <div role="dialog" aria-modal="true">
          <p>{searchParams.origin?.iata_code ?? ''} → {searchParams.destination?.iata_code ?? ''}</p>
          <p>{searchParams.trip_type === 'one_way' ? 'One Way' : 'Round Trip'}</p>
          <p>{searchParams.departure_date_from} to {searchParams.departure_date_to}</p>
          <div>
            <label htmlFor="track-email">Alert email</label>
            <input
              id="track-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="track-threshold">Price threshold ({currency})</label>
            <input
              id="track-threshold"
              type="number"
              min="0.01"
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
          </div>
          {formError && <p role="alert">{formError}</p>}
          <button onClick={handleSave} disabled={submitting}>Save</button>
          <button onClick={handleCancel}>Cancel</button>
        </div>
      )}
    </>
  );
}
