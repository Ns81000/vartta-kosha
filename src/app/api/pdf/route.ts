import { NextRequest, NextResponse } from 'next/server';
import { 
  fetchLiveData, 
  joinUrl,
  decryptEntry,
  findMatchingKey,
} from '@/lib/api/tradingref';
import { validateDateString } from '@/lib/utils/sanitize';
import { IMAGE_PROXY_BASE } from '@/lib/constants';
import { PDFDocument } from 'pdf-lib';
import { spawn } from 'node:child_process';
import path from 'node:path';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

interface PdfRequest {
  date: string;
  language: string;
  newspaper: string;
  edition: string;
}

type SniffedFileType =
  | 'pdf'
  | 'jpg'
  | 'png'
  | 'webp'
  | 'gif'
  | 'svg'
  | 'html'
  | 'json'
  | 'text'
  | 'unknown';

interface DownloadedAsset {
  data: Uint8Array;
  fileType: SniffedFileType;
}

interface GeneratedPdfResult {
  pdfData: Uint8Array | null;
  pagesAdded: number;
}

interface LockedPdfMergeResult extends GeneratedPdfResult {
  failures: string[];
}

function startsWithBytes(data: Uint8Array, signature: number[]): boolean {
  if (data.length < signature.length) return false;
  for (let i = 0; i < signature.length; i++) {
    if (data[i] !== signature[i]) return false;
  }
  return true;
}

function toAsciiPrefix(data: Uint8Array, max = 256): string {
  const prefix = data.slice(0, max);
  return new TextDecoder('utf-8', { fatal: false }).decode(prefix).trim().toLowerCase();
}

function sniffFileType(data: Uint8Array, contentType: string, sourceUrl: string): SniffedFileType {
  const ct = contentType.toLowerCase();

  if (ct.includes('application/pdf')) return 'pdf';
  if (ct.includes('image/jpeg') || ct.includes('image/jpg')) return 'jpg';
  if (ct.includes('image/png')) return 'png';
  if (ct.includes('image/webp')) return 'webp';
  if (ct.includes('image/gif')) return 'gif';
  if (ct.includes('image/svg')) return 'svg';
  if (ct.includes('application/json')) return 'json';
  if (ct.includes('text/html')) return 'html';
  if (ct.startsWith('text/')) return 'text';

  if (startsWithBytes(data, [0x25, 0x50, 0x44, 0x46])) return 'pdf';
  if (startsWithBytes(data, [0xff, 0xd8, 0xff])) return 'jpg';
  if (startsWithBytes(data, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return 'png';
  if (startsWithBytes(data, [0x47, 0x49, 0x46, 0x38])) return 'gif';
  if (
    startsWithBytes(data, [0x52, 0x49, 0x46, 0x46]) &&
    data.length >= 12 &&
    data[8] === 0x57 &&
    data[9] === 0x45 &&
    data[10] === 0x42 &&
    data[11] === 0x50
  ) {
    return 'webp';
  }

  const textPrefix = toAsciiPrefix(data);
  if (textPrefix.startsWith('<!doctype html') || textPrefix.startsWith('<html')) return 'html';
  if (textPrefix.startsWith('{') || textPrefix.startsWith('[')) return 'json';
  if (textPrefix.includes('<svg')) return 'svg';

  const path = sourceUrl.toLowerCase();
  if (path.endsWith('.pdf')) return 'pdf';
  if (path.endsWith('.jpg') || path.endsWith('.jpeg')) return 'jpg';
  if (path.endsWith('.png')) return 'png';

  return 'unknown';
}

async function downloadAsset(url: string): Promise<DownloadedAsset | null> {
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        Accept: 'application/pdf,image/*,*/*',
      },
      cache: 'no-store',
    });
    if (!response.ok) return null;

    const contentType = response.headers.get('content-type') ?? '';
    const data = new Uint8Array(await response.arrayBuffer());
    if (!data.length) return null;

    return {
      data,
      fileType: sniffFileType(data, contentType, url),
    };
  } catch {
    return null;
  }
}

async function downloadProxyImage(url: string): Promise<DownloadedAsset | null> {
  try {
    const proxyUrl = `${IMAGE_PROXY_BASE}/?url=${encodeURIComponent(url)}&maxage=1d&output=jpg&q=80`;
    const response = await fetch(proxyUrl);
    if (!response.ok) return null;

    const data = new Uint8Array(await response.arrayBuffer());
    if (!data.length) return null;

    return {
      data,
      fileType: 'jpg',
    };
  } catch {
    return null;
  }
}

async function addImageToPdf(pdfDoc: PDFDocument, data: Uint8Array): Promise<boolean> {
  try {
    let image;
    try {
      image = await pdfDoc.embedJpg(data);
    } catch {
      image = await pdfDoc.embedPng(data);
    }

    const page = pdfDoc.addPage([image.width, image.height]);
    page.drawImage(image, {
      x: 0,
      y: 0,
      width: image.width,
      height: image.height,
    });
    return true;
  } catch {
    return false;
  }
}

async function addPdfToPdf(target: PDFDocument, data: Uint8Array): Promise<number> {
  try {
    let source: PDFDocument;
    try {
      source = await PDFDocument.load(data);
    } catch {
      source = await PDFDocument.load(data, { ignoreEncryption: true });
    }

    const indices = source.getPageIndices();
    if (!indices.length) return 0;
    const pages = await target.copyPages(source, indices);
    pages.forEach((page) => target.addPage(page));
    return pages.length;
  } catch {
    return 0;
  }
}

async function generatePdfFromUrls(urls: string[]): Promise<GeneratedPdfResult> {
  const mergedPdf = await PDFDocument.create();
  let pagesAdded = 0;

  for (const url of urls) {
    const asset = await downloadAsset(url);
    if (!asset) continue;

    if (asset.fileType === 'pdf') {
      const pdfPages = await addPdfToPdf(mergedPdf, asset.data);
      if (pdfPages > 0) {
        pagesAdded += pdfPages;
        continue;
      }

      const proxyAsset = await downloadProxyImage(url);
      if (proxyAsset) {
        const ok = await addImageToPdf(mergedPdf, proxyAsset.data);
        if (ok) pagesAdded += 1;
      }
      continue;
    }

    if (asset.fileType === 'jpg' || asset.fileType === 'png') {
      const ok = await addImageToPdf(mergedPdf, asset.data);
      if (ok) pagesAdded += 1;
      continue;
    }

    const proxyAsset = await downloadProxyImage(url);
    if (!proxyAsset) continue;

    const ok = await addImageToPdf(mergedPdf, proxyAsset.data);
    if (ok) pagesAdded += 1;
  }

  if (!pagesAdded) {
    return { pdfData: null, pagesAdded: 0 };
  }

  return {
    pdfData: await mergedPdf.save(),
    pagesAdded,
  };
}

function buildPasswordMap(urls: string[]): Record<string, string> {
  const map: Record<string, string> = {};

  for (const url of urls) {
    try {
      const pathname = new URL(url).pathname;
      const fileName = pathname.split('/').pop() ?? '';
      if (!fileName) continue;
      map[fileName] = fileName.slice(0, 10);
    } catch {
      continue;
    }
  }

  return map;
}

async function mergeLockedPdfsWithPython(urls: string[]): Promise<LockedPdfMergeResult> {
  if (!urls.length) {
    return { pdfData: null, pagesAdded: 0, failures: [] };
  }

  const scriptPath = path.join(process.cwd(), 'scripts', 'merge_locked_pdfs.py');
  const inputPayload = JSON.stringify({
    urls,
    passwords: buildPasswordMap(urls),
  });

  return await new Promise<LockedPdfMergeResult>((resolve) => {
    const child = spawn('python', [scriptPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });

    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });

    child.on('error', (error) => {
      resolve({
        pdfData: null,
        pagesAdded: 0,
        failures: [`Python process failed: ${error.message}`],
      });
    });

    child.on('close', (code) => {
      if (code !== 0 && !stdout.trim()) {
        resolve({
          pdfData: null,
          pagesAdded: 0,
          failures: [stderr.trim() || `Python exited with code ${code}`],
        });
        return;
      }

      try {
        const parsed = JSON.parse(stdout || '{}') as {
          ok?: boolean;
          pagesAdded?: number;
          pdfBase64?: string;
          failures?: string[];
          error?: string;
        };

        if (!parsed.ok || !parsed.pdfBase64) {
          const failures = parsed.failures && parsed.failures.length
            ? parsed.failures
            : [parsed.error || 'Locked PDF merge returned no output'];
          resolve({
            pdfData: null,
            pagesAdded: 0,
            failures,
          });
          return;
        }

        resolve({
          pdfData: new Uint8Array(Buffer.from(parsed.pdfBase64, 'base64')),
          pagesAdded: parsed.pagesAdded ?? 0,
          failures: parsed.failures ?? [],
        });
      } catch {
        resolve({
          pdfData: null,
          pagesAdded: 0,
          failures: [stderr.trim() || 'Failed to parse Python merge response'],
        });
      }
    });

    child.stdin.write(inputPayload);
    child.stdin.end();
  });
}

export async function POST(request: NextRequest) {
  try {
    const body: PdfRequest = await request.json();
    const { date, language, newspaper, edition } = body;
    
    // Validate inputs
    if (!date || !language || !newspaper || !edition) {
      return NextResponse.json(
        { success: false, error: 'Missing required parameters' },
        { status: 400 }
      );
    }
    
    if (!validateDateString(date)) {
      return NextResponse.json(
        { success: false, error: 'Invalid date format' },
        { status: 400 }
      );
    }
    
    // Fetch live data from TradingRef
    const liveData = await fetchLiveData(date);
    
    if (liveData) {
      const originalLangKey = findMatchingKey(Object.keys(liveData), language);
      
      if (originalLangKey && liveData[originalLangKey]) {
        const originalPaperKey = findMatchingKey(
          Object.keys(liveData[originalLangKey]),
          newspaper
        );
        
        if (originalPaperKey && liveData[originalLangKey][originalPaperKey]) {
          const originalEditionKey = findMatchingKey(
            Object.keys(liveData[originalLangKey][originalPaperKey]),
            edition
          );
          
          if (originalEditionKey) {
            const obfuscated = liveData[originalLangKey][originalPaperKey][originalEditionKey];
            const entry = decryptEntry(obfuscated);
            
            if (entry.pages.length > 0) {
              const urls = entry.pages.map(page => joinUrl(entry.prefix, page));
              const normalizedType = entry.type === 'dfl' ? 'pdfl' : entry.type;

              let pdfData: Uint8Array | null = null;
              let pagesAdded = 0;
              let generationFailures: string[] = [];

              if (normalizedType === 'pdfl') {
                const lockedResult = await mergeLockedPdfsWithPython(urls);
                pdfData = lockedResult.pdfData;
                pagesAdded = lockedResult.pagesAdded;
                generationFailures = lockedResult.failures;

                // If Python decryption fails, try image fallback as a last resort.
                if (!pdfData) {
                  const fallback = await generatePdfFromUrls(urls);
                  pdfData = fallback.pdfData;
                  pagesAdded = fallback.pagesAdded;
                }
              } else {
                const generated = await generatePdfFromUrls(urls);
                pdfData = generated.pdfData;
                pagesAdded = generated.pagesAdded;
              }
              
              if (pdfData) {
                // Return as base64 data URL
                const base64 = Buffer.from(pdfData).toString('base64');
                const dataUrl = `data:application/pdf;base64,${base64}`;
                
                return NextResponse.json({
                  success: true,
                  pdfUrl: dataUrl,
                  pagesAdded,
                  source: 'live',
                  isPasswordProtected: normalizedType === 'pdfl',
                });
              }

              return NextResponse.json(
                {
                  success: false,
                  error:
                    'No printable pages were returned for this edition. The source may be locked or unavailable right now.',
                  details: generationFailures,
                },
                { status: 422 }
              );
            }
          }
        }
      }
    }
    
    return NextResponse.json(
      { success: false, error: 'Unable to generate PDF. The newspaper may not be available.' },
      { status: 404 }
    );
    
  } catch (error) {
    console.error('PDF API error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to generate PDF. Please try again.' },
      { status: 500 }
    );
  }
}
