'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Newspaper, BookOpen, RefreshCw } from 'lucide-react';
import { useNewspaper } from '@/hooks/use-newspaper';
import { DatePicker } from '@/components/features/date-picker';
import { NeumorphicSelect } from '@/components/ui/neumorphic-select';
import { NeumorphicCard } from '@/components/ui/neumorphic-card';
import { NeumorphicButton } from '@/components/ui/neumorphic-button';
import { PdfViewer } from '@/components/features/pdf-viewer';
import { cn } from '@/lib/utils/cn';

export default function Home() {
  const {
    date,
    language,
    newspaper,
    edition,
    languages,
    newspapers,
    editions,
    pdfUrl,
    error,
    progress,
    loading,
    setDate,
    setLanguage,
    setNewspaper,
    setEdition,
    fetchPdf,
    reset,
    canFetchPdf,
    isAnyLoading,
  } = useNewspaper();

  const languageOptions = languages.map(l => ({
    value: l.id,
    label: l.name,
    sublabel: l.nativeName !== l.name ? l.nativeName : undefined,
  }));

  const newspaperOptions = newspapers.map(n => ({
    value: n.id,
    label: n.name,
  }));

  const editionOptions = editions.map(e => ({
    value: e.id,
    label: e.name,
    sublabel: e.pagesCount ? `${e.pagesCount} pages` : undefined,
  }));

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      {/* Fixed Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-effect border-b border-[var(--shadow-dark)]/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 sm:h-20">
            {/* Logo */}
            <motion.div 
              className="flex items-center gap-3"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className={cn(
                'w-10 h-10 sm:w-12 sm:h-12 rounded-xl',
                'bg-[var(--bg-elevated)]',
                'shadow-[4px_4px_8px_var(--shadow-dark),-4px_-4px_8px_var(--shadow-light)]',
                'flex items-center justify-center'
              )}>
                <Newspaper className="w-5 h-5 sm:w-6 sm:h-6 text-[var(--accent-primary)]" />
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-bold font-[var(--font-heading)] text-[var(--text-primary)]">
                  Vārttā Kōśa
                </h1>
                <p className="text-xs sm:text-sm text-[var(--text-muted)] hidden sm:block">
                  वार्त्ता कोश
                </p>
              </div>
            </motion.div>

            {/* Right side */}
            <div className="flex items-center gap-3">
              {isAnyLoading && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={cn(
                    'inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm',
                    'bg-[var(--bg-elevated)]',
                    'shadow-[3px_3px_6px_var(--shadow-dark),-3px_-3px_6px_var(--shadow-light)]'
                  )}
                >
                  <div className="w-2 h-2 rounded-full bg-[var(--accent-primary)] animate-pulse" />
                  <span className="text-[var(--text-muted)]">Loading...</span>
                </motion.div>
              )}
              
              {(date || pdfUrl) && (
                <NeumorphicButton
                  variant="ghost"
                  size="sm"
                  onClick={reset}
                  className="hidden sm:flex"
                >
                  <RefreshCw className="w-4 h-4" />
                  Reset
                </NeumorphicButton>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Spacer for fixed header */}
      <div className="h-16 sm:h-20" />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10">
        {/* Hero Section - shown when nothing selected */}
        <AnimatePresence mode="wait">
          {!date && (
            <motion.div
              key="hero"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="text-center mb-10 sm:mb-16"
            >
              <motion.div
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: 'spring' }}
                className={cn(
                  'w-20 h-20 sm:w-24 sm:h-24 mx-auto mb-6 rounded-3xl',
                  'bg-[var(--bg-elevated)]',
                  'shadow-[12px_12px_24px_var(--shadow-dark),-12px_-12px_24px_var(--shadow-light)]',
                  'flex items-center justify-center'
                )}
              >
                <BookOpen className="w-10 h-10 sm:w-12 sm:h-12 text-[var(--accent-primary)]" />
              </motion.div>
              
              <h2 className="text-2xl sm:text-4xl font-bold font-[var(--font-heading)] text-[var(--text-primary)] mb-3">
                The Chronicle Vault
              </h2>
              <p className="text-base sm:text-lg text-[var(--text-secondary)] max-w-lg mx-auto mb-2">
                Access Indian newspapers from across 14 languages
              </p>
              <p className="text-sm text-[var(--text-muted)] italic">
                &ldquo;Where yesterday&apos;s news becomes tomorrow&apos;s history&rdquo;
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
          {/* Selection Panel */}
          <motion.div 
            className="lg:col-span-1"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
          >
            <NeumorphicCard className="space-y-6">
              <div className="flex items-center gap-3 mb-2">
                <div className={cn(
                  'w-8 h-8 rounded-lg',
                  'bg-[var(--accent-primary)]/10',
                  'flex items-center justify-center'
                )}>
                  <Newspaper className="w-4 h-4 text-[var(--accent-primary)]" />
                </div>
                <h3 className="text-lg font-semibold font-[var(--font-heading)] text-[var(--text-primary)]">
                  Select Newspaper
                </h3>
              </div>

              {/* Date Picker */}
              <DatePicker
                value={date}
                onChange={setDate}
              />

              {/* Language Selector */}
              <NeumorphicSelect
                label="Language"
                options={languageOptions}
                value={language}
                onChange={setLanguage}
                placeholder={date ? "Select language..." : "Select date first"}
                disabled={!date || loading.languages}
                loading={loading.languages}
              />

              {/* Newspaper Selector */}
              <NeumorphicSelect
                label="Newspaper"
                options={newspaperOptions}
                value={newspaper}
                onChange={setNewspaper}
                placeholder={language ? "Select newspaper..." : "Select language first"}
                disabled={!language || loading.newspapers}
                loading={loading.newspapers}
              />

              {/* Edition Selector */}
              <NeumorphicSelect
                label="Edition"
                options={editionOptions}
                value={edition}
                onChange={setEdition}
                placeholder={newspaper ? "Select edition..." : "Select newspaper first"}
                disabled={!newspaper || loading.editions}
                loading={loading.editions}
              />

              {/* Fetch Button */}
              <NeumorphicButton
                variant="primary"
                className="w-full"
                size="lg"
                disabled={!canFetchPdf || loading.pdf}
                loading={loading.pdf}
                onClick={fetchPdf}
              >
                {loading.pdf ? 'Generating PDF...' : 'Fetch Newspaper PDF'}
              </NeumorphicButton>

              {/* Error Display */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className={cn(
                      'p-3 rounded-xl',
                      'bg-[var(--state-error)]/10',
                      'border border-[var(--state-error)]/20'
                    )}
                  >
                    <p className="text-sm text-[var(--state-error)]">{error}</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </NeumorphicCard>

            {/* Info Card */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="mt-6"
            >
              <NeumorphicCard variant="pressed" padding="sm">
                <div className="text-xs text-[var(--text-muted)] space-y-1">
                  <p><strong>Available:</strong> Jul 29, 2025 - Today</p>
                  <p><strong>Languages:</strong> 14 regional languages</p>
                  <p><strong>Newspapers:</strong> 100+ publications</p>
                </div>
              </NeumorphicCard>
            </motion.div>
          </motion.div>

          {/* PDF Viewer Panel */}
          <motion.div 
            className="lg:col-span-2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <NeumorphicCard className="min-h-[500px]">
              <PdfViewer
                pdfUrl={pdfUrl}
                progress={progress}
                error={loading.pdf ? null : error}
                onRetry={canFetchPdf ? fetchPdf : undefined}
              />
            </NeumorphicCard>
          </motion.div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto py-6 border-t border-[var(--shadow-dark)]/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[var(--text-muted)]">
            <p>
              © {new Date().getFullYear()} Vārttā Kōśa. The Chronicle Vault.
            </p>
            <p className="text-xs">
              Indian Newspaper Archive • 14 Languages • 100+ Publications
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
