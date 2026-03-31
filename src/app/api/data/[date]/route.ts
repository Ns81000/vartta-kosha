import { NextRequest, NextResponse } from 'next/server';
import { 
  fetchLiveData, 
  extractLanguages 
} from '@/lib/api/tradingref';
import { validateDateString } from '@/lib/utils/sanitize';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

interface RouteParams {
  params: Promise<{ date: string }>;
}

export async function GET(
  request: NextRequest,
  { params }: RouteParams
) {
  try {
    const { date } = await params;
    
    // Validate date format
    if (!validateDateString(date)) {
      return NextResponse.json(
        { success: false, error: 'Invalid date format. Use YYYYMMDD.' },
        { status: 400 }
      );
    }
    
    // Fetch live data from TradingRef
    const liveData = await fetchLiveData(date);
    
    if (liveData && Object.keys(liveData).length > 0) {
      const languages = extractLanguages(liveData);
      
      return NextResponse.json({
        success: true,
        date,
        languages,
        languageCount: languages.length,
        source: 'live',
      });
    }
    
    // No data available
    return NextResponse.json(
      { 
        success: false, 
        error: 'No newspaper data available for this date. Please try another date.',
        date 
      },
      { status: 404 }
    );
    
  } catch (error) {
    console.error('Date API error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch newspaper data. Please try again.' },
      { status: 500 }
    );
  }
}
