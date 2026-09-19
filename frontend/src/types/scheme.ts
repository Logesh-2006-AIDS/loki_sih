export interface EligibilityRuleItem {
  field: string;
  operator: string;
  value: any;
  label?: string;
  description?: string;
  pass_message?: string;
  fail_message?: string;
}

export interface EligibilityRulesConfig {
  disclaimer?: string;
  community?: string;
  min_qualifying_percentage?: number;
  max_annual_family_income?: number;
  max_age?: number;
  valid_course_types?: string[];
  rules?: EligibilityRuleItem[];
  [key: string]: any;
}

export interface SchemeVersion {
  id: string;
  scheme_id: string;
  scheme_code: string;
  scheme_version: string;
  name: string;
  description?: string | null;
  is_demo: boolean;
  eligibility_rules: EligibilityRulesConfig;
  form_schema: Record<string, any>;
  required_documents: {
    disclaimer?: string;
    documents?: Array<{
      type: string;
      label: string;
      required: boolean;
      description?: string;
    }>;
    [key: string]: any;
  };
  scoring_weights: Record<string, any>;
  effective_from?: string | null;
  effective_to?: string | null;
  is_active: boolean;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
}

export interface Scheme {
  id: string;
  scheme_code: string;
  name: string;
  description?: string | null;
  scheme_version: string;
  is_demo: boolean;
  eligibility_rules: EligibilityRulesConfig;
  form_schema: Record<string, any>;
  required_documents: Record<string, any>;
  scoring_weights: Record<string, any>;
  deadline?: string | null;
  is_active: boolean;
  active_version_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SchemeDetail extends Scheme {
  active_version?: SchemeVersion | null;
  versions_count: number;
}

export interface RuleCheckDetail {
  rule: string;
  label: string;
  operator: string;
  expected: any;
  actual: any;
  passed: boolean;
  message: string;
}

export interface EligibilityCheckResponse {
  eligible: boolean;
  summary_message: string;
  disclaimer: string;
  is_demo: boolean;
  checks: RuleCheckDetail[];
}

export interface UserProfile {
  id: string;
  full_name: string;
  email: string;
  role: 'APPLICANT' | 'OFFICER' | 'COMMITTEE' | 'ADMIN';
  is_active: boolean;
}
