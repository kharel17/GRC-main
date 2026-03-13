export interface ControlMatchItem {
  controlAnnex: string;
  title: string;
  confidence: number;
  excerpt?: string;
}

export interface SecurityPracticeItem {
  practice: string;
  relatedControls: string[];
}

export interface DocumentAnalysis {
  id: string;
  organizationId: string;
  fileName: string;
  fileUrl?: string;
  fileSize?: number;
  fileType?: string;
  status: 'pending' | 'analyzing' | 'completed' | 'failed';
  documentCategory?: string;
  analysisResult?: any;
  implementedControls?: any[];
  missingControls?: any[];
  securityPractices?: SecurityPracticeItem[];
  evidenceId?: string;
  createdAt: string;
  analyzedAt?: string;
}

export interface DocumentAnalysisSummary {
  id: string;
  fileName: string;
  status: string;
  documentCategory?: string;
  implementedCount: number;
  missingCount: number;
  createdAt: string;
}
