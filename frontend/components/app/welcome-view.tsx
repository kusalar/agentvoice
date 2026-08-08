'use client';

import React from 'react';
import {
  BadgeCheck,
  Coffee,
  Heart,
  HelpCircle,
  Package,
  ShoppingBag,
  Sparkles,
  Store,
  Truck,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

const LOCAL_PRODUCTS = [
  {
    id: 1,
    name: 'Fresh Organic Wildflower Honey',
    weight: '500g jar',
    price: '₹450',
    usd: '$5.99',
    vendor: 'Local Apiary Farms',
    badge: 'In Stock',
    badgeColor: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    icon: '🍯',
    desc: 'Pure, raw, 100% natural organic honey harvested locally.',
  },
  {
    id: 2,
    name: 'Handcrafted Sourdough Bread',
    weight: '750g loaf',
    price: '₹220',
    usd: '$2.99',
    vendor: 'Artisan Local Bakery',
    badge: 'Baked Daily',
    badgeColor: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    icon: '🍞',
    desc: 'Naturally fermented sourdough baked fresh every morning.',
  },
  {
    id: 3,
    name: 'Artisanal Roasted Coffee Beans',
    weight: '250g pack',
    price: '₹580',
    usd: '$7.50',
    vendor: 'Mountain Roast Co.',
    badge: 'Best Seller',
    badgeColor: 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20',
    icon: '☕',
    desc: 'Single-origin medium roast, available as whole bean or ground.',
  },
  {
    id: 4,
    name: 'Handmade Ceramic Tea Mug',
    weight: '350ml cup',
    price: '₹350',
    usd: '$4.50',
    vendor: 'Heritage Pottery Crafts',
    badge: 'Limited Stock',
    badgeColor: 'bg-rose-500/10 text-rose-500 border-rose-500/20',
    icon: '🏺',
    desc: 'Artisanal hand-painted pottery mug with ergonomic handle.',
  },
  {
    id: 5,
    name: 'Organic Cold-Pressed Coconut Oil',
    weight: '1 Litre bottle',
    price: '₹650',
    usd: '$8.25',
    vendor: 'Green Harvest Organics',
    badge: 'In Stock',
    badgeColor: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    icon: '🥥',
    desc: 'Unrefined extra-virgin oil cold-pressed from local coconuts.',
  },
  {
    id: 6,
    name: 'Handwoven Cotton Tote Bag',
    weight: 'Eco Edition',
    price: '₹399',
    usd: '$4.99',
    vendor: 'EcoWeave Local',
    badge: 'Eco Friendly',
    badgeColor: 'bg-cyan-500/10 text-cyan-500 border-cyan-500/20',
    icon: '🛍️',
    desc: '100% sustainable organic cotton bag with reinforced handles.',
  },
];

const SAMPLE_PROMPTS = [
  'How much is the Organic Honey?',
  'Do you have fresh Sourdough Bread?',
  'What items are under ₹400?',
  'Tell me about delivery fees',
];

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
  ...props
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div
      ref={ref}
      className="flex min-h-[90vh] w-full flex-col items-center justify-start px-4 py-8 md:px-8 md:py-12"
      {...props}
    >
      <section className="relative flex w-full max-w-5xl flex-col items-center justify-center rounded-3xl border border-border/60 bg-card/50 p-6 text-center shadow-2xl backdrop-blur-2xl md:p-10">
        {/* Ambient Decorative Backdrop Gradients */}
        <div className="pointer-events-none absolute -top-20 left-1/2 size-96 -translate-x-1/2 rounded-full bg-gradient-to-tr from-indigo-500/20 via-purple-500/20 to-emerald-500/20 blur-3xl" />

        {/* Top Header Tag */}
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-emerald-500 dark:text-emerald-400">
          <BadgeCheck className="size-4 text-emerald-500" />
          <span>Verified Local Market Network</span>
          <span className="size-1.5 rounded-full bg-emerald-500 animate-ping" />
        </div>

        {/* Main Title Requested by User */}
        <h1 className="bg-gradient-to-r from-foreground via-primary to-emerald-400 bg-clip-text text-3xl font-black tracking-tight text-transparent sm:text-4xl md:text-5xl">
          LOCAL COMMERCE ASSISTANT
        </h1>

        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground md:text-base">
          Your instant voice AI companion for discovering local products, checking real-time store prices, verifying stock, and managing local deliveries.
        </p>

        {/* Store Highlights Bar */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3 text-xs font-medium text-muted-foreground">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-muted/60 px-3 py-1 border border-border/40">
            <Truck className="size-3.5 text-indigo-400" /> Free Delivery over ₹499
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-muted/60 px-3 py-1 border border-border/40">
            <Store className="size-3.5 text-emerald-400" /> Open 8 AM – 9 PM
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-muted/60 px-3 py-1 border border-border/40">
            <Package className="size-3.5 text-amber-400" /> Same-Day Local Dispatch
          </span>
        </div>

        {/* Local Product Catalog Grid */}
        <div className="mt-8 w-full text-left">
          <div className="mb-4 flex items-center justify-between px-1">
            <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-foreground">
              <ShoppingBag className="size-4 text-primary" />
              Featured Local Product Catalog
            </h2>
            <span className="text-xs text-muted-foreground">Prices live in store</span>
          </div>

          <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
            {LOCAL_PRODUCTS.map((prod) => (
              <div
                key={prod.id}
                className="group relative flex flex-col justify-between rounded-2xl border border-border/50 bg-background/60 p-4 transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-lg dark:bg-zinc-900/60"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-2xl">{prod.icon}</span>
                    <span
                      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${prod.badgeColor}`}
                    >
                      {prod.badge}
                    </span>
                  </div>

                  <h3 className="mt-2.5 font-bold text-foreground text-sm group-hover:text-primary transition-colors">
                    {prod.name}
                  </h3>
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                    {prod.desc}
                  </p>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-border/40 pt-3">
                  <div>
                    <span className="text-xs text-muted-foreground font-mono">{prod.vendor}</span>
                    <p className="text-xs font-semibold text-muted-foreground">{prod.weight}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-base font-extrabold text-foreground">{prod.price}</span>
                    <span className="ml-1 text-[11px] text-muted-foreground font-mono">({prod.usd})</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sample Voice Prompts */}
        <div className="mt-8 w-full">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Sample Questions You Can Ask the Assistant:
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2">
            {SAMPLE_PROMPTS.map((prompt, i) => (
              <button
                key={i}
                onClick={onStartCall}
                className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3.5 py-1.5 text-xs font-medium text-foreground transition-all hover:bg-primary/15 hover:border-primary/40"
              >
                <HelpCircle className="size-3 text-primary" />
                "{prompt}"
              </button>
            ))}
          </div>
        </div>

        {/* ONE Clear Primary Call Button */}
        <div className="mt-9 flex flex-col items-center gap-2">
          <Button
            size="lg"
            onClick={onStartCall}
            className="group relative h-14 min-w-[280px] gap-3 rounded-full bg-primary px-8 text-sm font-bold uppercase tracking-wider text-primary-foreground shadow-2xl shadow-primary/40 transition-all duration-300 hover:scale-105 hover:bg-primary/90 focus:ring-4 focus:ring-primary/20"
          >
            <Sparkles className="size-5 animate-spin-slow text-primary-foreground" />
            <span>{startButtonText || 'Start Shopping Conversation'}</span>
            <ShoppingBag className="size-5 transition-transform group-hover:translate-x-1" />
          </Button>
          <span className="text-[11px] text-muted-foreground">
            Click to connect to your local voice assistant
          </span>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-8 text-center">
        <p className="text-xs text-muted-foreground">
          Powered by <strong className="text-foreground">Murf Falcon Voice AI</strong> & LiveKit Agents
        </p>
      </footer>
    </div>
  );
};
