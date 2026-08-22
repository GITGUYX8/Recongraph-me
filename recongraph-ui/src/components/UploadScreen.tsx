"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface UploadScreenProps {
  onDemoLoad: () => void;
  isLoading: boolean;
}

export default function UploadScreen({ onDemoLoad, isLoading }: UploadScreenProps) {
  return (
    <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-8 items-center mt-10 animate-in fade-in duration-300 min-h-[70vh]">
      {/* Left: Background with overlay and content */}
      <div className="relative lg:col-span-1">
        <div className="absolute inset-0 bg-gradient-to-br from-background/90 via-background/70 to-background/50" aria-hidden="true" />
        <div className="relative p-8 lg:p-12 h-full flex flex-col justify-center">
          <h2 className="text-4xl lg:text-5xl font-bold tracking-tight text-foreground text-balance mb-6">
            Reconcile with Confidence.
          </h2>
          <p className="text-base lg:text-lg text-muted-foreground leading-relaxed max-w-md mb-8">
            The deterministic graph engine that proves every match and explains
            every conflict — with strict conservation. No data loss, ever.
          </p>
          <div className="grid grid-cols-3 gap-4">
            <Card className="p-4 bg-background/80 backdrop-blur-sm border-border/50">
              <div className="text-xs text-muted-foreground">
                <span className="text-success font-semibold">0</span> false positives
              </div>
              <div className="text-xs text-muted-foreground">
                on adversarial corpus
              </div>
            </Card>
            <Card className="p-4 bg-background/80 backdrop-blur-sm border-border/50">
              <div className="text-xs text-muted-foreground">
                Threshold <span className="font-mono text-foreground">0.95</span>
              </div>
              <div className="text-xs text-muted-foreground">
                calibrated on challenge set
              </div>
            </Card>
            <Card className="p-4 bg-background/80 backdrop-blur-sm border-border/50">
              <div className="text-xs text-muted-foreground">
                In = Out <span className="text-success">guaranteed</span>
              </div>
              <div className="text-xs text-muted-foreground">
                strict conservation
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* Right: action panel */}
      <div className="lg:col-span-1 flex justify-center">
        <Card className="w-full max-w-md bg-background/90 backdrop-blur-sm border-border/50">
          <CardContent className="flex flex-col gap-5 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label
                className={`border-2 border-dashed border-border rounded-lg p-6 flex flex-col items-center justify-center text-center transition-colors cursor-pointer ${
                  isLoading ? 'opacity-50 pointer-events-none' : 'hover:bg-muted/50 hover:border-primary/50'
                }`}
              >
                <input type="file" accept=".csv" className="hidden" onChange={onDemoLoad} disabled={isLoading} />
                <svg aria-hidden="true" className="w-7 h-7 text-muted-foreground mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span className="font-medium text-sm">Purchase Register (CSV)</span>
                <span className="text-xs text-muted-foreground mt-1">Click or drag file to upload</span>
              </label>

              <label
                className={`border-2 border-dashed border-border rounded-lg p-6 flex flex-col items-center justify-center text-center transition-colors cursor-pointer ${
                  isLoading ? 'opacity-50 pointer-events-none' : 'hover:bg-muted/50 hover:border-primary/50'
                }`}
              >
                <input type="file" accept=".csv" className="hidden" onChange={onDemoLoad} disabled={isLoading} />
                <svg aria-hidden="true" className="w-7 h-7 text-muted-foreground mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span className="font-medium text-sm">GST Records (CSV)</span>
                <span className="text-xs text-muted-foreground mt-1">Click or drag file to upload</span>
              </label>
            </div>

            <div className="w-full flex items-center gap-4" aria-hidden="true">
              <div className="h-px bg-border flex-1"></div>
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Or try it out</span>
              <div className="h-px bg-border flex-1"></div>
            </div>

            <Button
              variant="accent"
              size="lg"
              className="w-full"
              onClick={onDemoLoad}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <svg aria-hidden="true" className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span role="status">Executing Engine...</span>
                </>
              ) : (
                "Load Demo Dataset (Challenge Referee)"
              )}
            </Button>

            <p className="text-xs text-muted-foreground text-center">
              Adversarial challenge corpus — auto-match threshold calibrated at 0.95.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
