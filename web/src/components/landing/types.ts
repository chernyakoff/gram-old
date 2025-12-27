import type { Component } from 'vue';

export interface NavItem {
  label: string;
  href: string;
}

export interface Feature {
  title: string;
  description: string;
  icon: Component;
}

export interface Step {
  number: string;
  title: string;
  description: string;
  icon: Component;
}

export interface ComparisonPoint {
  feature: string;
  oldWay: string;
  newWay: string;
}

export interface PricingPlan {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  isPopular?: boolean;
  buttonText: string;
}

export interface TeamMember {
  name: string;
  role: string;
  imageUrl: string;
  bio: string;
  socials?: {
    linkedin?: string;
    twitter?: string;
  };
}

export interface Testimonial {
  content: string;
  author: string;
  role: string;
  company: string;
  avatarUrl: string;
}

export interface FAQItem {
  question: string;
  answer: string;
}
