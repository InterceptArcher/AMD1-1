import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PersonalizedContent from '../src/components/PersonalizedContent';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock window.open for PDF download
const mockWindowOpen = jest.fn();
window.open = mockWindowOpen;

const mockPersonalizationData = {
  intro_hook: 'Welcome back, John! As a Product Manager at TechCorp...',
  cta: 'Download your personalized guide now',
  first_name: 'John',
  company: 'TechCorp',
  title: 'Product Manager',
};

beforeEach(() => {
  mockFetch.mockClear();
  mockWindowOpen.mockClear();
  // Default mock for delivery endpoint (called on mount)
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      email_sent: true,
      pdf_url: 'https://example.com/ebook.pdf',
    }),
  });
});

describe('PersonalizedContent', () => {
  it('renders personalized greeting with name', async () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/hi john/i)).toBeInTheDocument();
  });

  it('renders personalized intro hook', async () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/welcome back, john/i)).toBeInTheDocument();
  });

  it('renders personalized CTA', async () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/download your personalized guide/i)).toBeInTheDocument();
  });

  it('renders company and title context', async () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/tailored insights for/i)).toBeInTheDocument();
  });

  it('handles missing optional fields gracefully', async () => {
    const partialData = {
      intro_hook: 'Discover powerful insights in this ebook!',
      cta: 'Get started today',
    };
    render(<PersonalizedContent data={partialData} />);
    expect(screen.getByText(/discover powerful insights/i)).toBeInTheDocument();
    expect(screen.getByText(/get started today/i)).toBeInTheDocument();
  });

  it('shows generic greeting when no name provided', async () => {
    const partialData = {
      intro_hook: 'Generic intro',
      cta: 'CTA text',
    };
    render(<PersonalizedContent data={partialData} />);
    expect(screen.getByText('Welcome!')).toBeInTheDocument();
  });

  it('displays error state when error prop is passed', () => {
    render(<PersonalizedContent data={null} error="Failed to load personalization" />);
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });

  it('renders nothing when data is null and no error', () => {
    const { container } = render(<PersonalizedContent data={null} />);
    expect(container.firstChild).toBeNull();
  });

  describe('Email Delivery', () => {
    const dataWithEmail = {
      ...mockPersonalizationData,
      email: 'john@techcorp.com',
    };

    it('automatically triggers email delivery when email is present', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          email_sent: true,
          pdf_url: 'https://example.com/ebook.pdf',
        }),
      });

      render(<PersonalizedContent data={dataWithEmail} />);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/rad/deliver/john%40techcorp.com',
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('shows success message when email is sent', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          email_sent: true,
          pdf_url: 'https://example.com/ebook.pdf',
        }),
      });

      render(<PersonalizedContent data={dataWithEmail} />);

      await waitFor(() => {
        expect(screen.getByText(/check your inbox/i)).toBeInTheDocument();
      });
    });

    it('shows fallback message when email fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          email_sent: false,
          pdf_url: 'https://example.com/ebook.pdf',
          email_error: 'No email provider configured',
        }),
      });

      render(<PersonalizedContent data={dataWithEmail} />);

      await waitFor(() => {
        expect(screen.getByText(/email delivery unavailable/i)).toBeInTheDocument();
      });
    });

    it('shows download button as fallback when email fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          email_sent: false,
          pdf_url: 'https://example.com/ebook.pdf',
        }),
      });

      render(<PersonalizedContent data={dataWithEmail} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /download your free ebook/i })).toBeInTheDocument();
      });
    });
  });

  describe('PDF Download Fallback', () => {
    const dataWithEmail = {
      ...mockPersonalizationData,
      email: 'john@techcorp.com',
    };

    // Mock URL.createObjectURL and URL.revokeObjectURL
    const mockCreateObjectURL = jest.fn(() => 'blob:http://localhost/mock-blob');
    const mockRevokeObjectURL = jest.fn();

    beforeEach(() => {
      global.URL.createObjectURL = mockCreateObjectURL;
      global.URL.revokeObjectURL = mockRevokeObjectURL;
      mockCreateObjectURL.mockClear();
      mockRevokeObjectURL.mockClear();
    });

    it('downloads PDF blob when download button is clicked', async () => {
      // First mock for delivery endpoint (auto-called on mount)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          email_sent: false,
          pdf_url: 'https://storage.example.com/ebook.pdf',
        }),
      });

      // Second mock for download endpoint
      const mockBlob = new Blob(['mock pdf content'], { type: 'application/pdf' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      render(<PersonalizedContent data={dataWithEmail} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /download your free ebook/i })).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download your free ebook/i });
      fireEvent.click(downloadButton);

      await waitFor(() => {
        // Verify the download endpoint was called
        expect(mockFetch).toHaveBeenCalledWith('/api/rad/download/john%40techcorp.com');
      });

      await waitFor(() => {
        // Verify blob URL was created for download
        expect(mockCreateObjectURL).toHaveBeenCalled();
      });
    });
  });
});
