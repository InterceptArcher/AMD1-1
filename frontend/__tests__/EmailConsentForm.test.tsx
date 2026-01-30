import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EmailConsentForm, { UserInputs } from '../src/components/EmailConsentForm';

describe('EmailConsentForm', () => {
  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  const fillForm = async (
    email = 'test@example.com',
    firstName = 'John',
    lastName = 'Doe',
    goal = 'exploring',
    persona = 'executive',
    industry = 'healthcare'
  ) => {
    const firstNameInput = screen.getByLabelText(/first name/i);
    await userEvent.type(firstNameInput, firstName);

    const lastNameInput = screen.getByLabelText(/last name/i);
    await userEvent.type(lastNameInput, lastName);

    const emailInput = screen.getByLabelText(/work email/i);
    await userEvent.type(emailInput, email);

    const goalSelect = screen.getByLabelText(/what brings you here/i);
    await userEvent.selectOptions(goalSelect, goal);

    const personaSelect = screen.getByLabelText(/what best describes your role/i);
    await userEvent.selectOptions(personaSelect, persona);

    const industrySelect = screen.getByLabelText(/what industry/i);
    await userEvent.selectOptions(industrySelect, industry);

    const checkbox = screen.getByRole('checkbox');
    await userEvent.click(checkbox);
  };

  it('renders name input fields', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
  });

  it('renders email input field', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    expect(screen.getByLabelText(/work email/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/company\.com/i)).toBeInTheDocument();
  });

  it('renders consent checkbox', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
    expect(screen.getByLabelText(/agree/i)).toBeInTheDocument();
  });

  it('renders submit button', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    expect(screen.getByRole('button', { name: /get my free ebook/i })).toBeInTheDocument();
  });

  it('renders dropdown selects for goal, persona, and industry', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    expect(screen.getByLabelText(/what brings you here/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/what best describes your role/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/what industry/i)).toBeInTheDocument();
  });

  it('submit button is disabled when form is empty', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const submitButton = screen.getByRole('button', { name: /get my free ebook/i });
    expect(submitButton).toBeDisabled();
  });

  it('submit button is disabled when only email is filled', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const emailInput = screen.getByLabelText(/work email/i);
    await userEvent.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: /get my free ebook/i });
    expect(submitButton).toBeDisabled();
  });

  it('submit button is disabled when dropdowns are not selected', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const emailInput = screen.getByLabelText(/work email/i);
    const checkbox = screen.getByRole('checkbox');

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.click(checkbox);

    const submitButton = screen.getByRole('button', { name: /get my free ebook/i });
    expect(submitButton).toBeDisabled();
  });

  it('submit button is enabled when all fields are completed', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    await fillForm();

    const submitButton = screen.getByRole('button', { name: /get my free ebook/i });
    expect(submitButton).toBeEnabled();
  });

  it('shows error for invalid email format', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const emailInput = screen.getByLabelText(/work email/i);

    await userEvent.type(emailInput, 'invalid-email');
    fireEvent.blur(emailInput);

    await waitFor(() => {
      expect(screen.getByText(/valid email/i)).toBeInTheDocument();
    });
  });

  it('calls onSubmit with all user inputs when form is submitted', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    await fillForm('test@example.com', 'Jane', 'Smith', 'evaluating', 'security', 'financial_services');

    const submitButton = screen.getByRole('button', { name: /get my free ebook/i });
    await userEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith({
      email: 'test@example.com',
      firstName: 'Jane',
      lastName: 'Smith',
      goal: 'evaluating',
      persona: 'security',
      industry: 'financial_services',
    });
  });

  it('disables form during submission', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} isLoading={true} />);

    const emailInput = screen.getByLabelText(/work email/i);
    const checkbox = screen.getByRole('checkbox');
    const submitButton = screen.getByRole('button', { name: /creating/i });

    expect(emailInput).toBeDisabled();
    expect(checkbox).toBeDisabled();
    expect(submitButton).toBeDisabled();
  });

  it('has correct dropdown options for goal', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const goalSelect = screen.getByLabelText(/what brings you here/i);

    expect(goalSelect).toContainHTML('exploring');
    expect(goalSelect).toContainHTML('evaluating');
    expect(goalSelect).toContainHTML('learning');
  });

  it('has correct dropdown options for persona', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const personaSelect = screen.getByLabelText(/what best describes your role/i);

    expect(personaSelect).toContainHTML('executive');
    expect(personaSelect).toContainHTML('security');
    expect(personaSelect).toContainHTML('data_ai');
  });

  it('has correct dropdown options for industry', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const industrySelect = screen.getByLabelText(/what industry/i);

    expect(industrySelect).toContainHTML('healthcare');
    expect(industrySelect).toContainHTML('financial_services');
    expect(industrySelect).toContainHTML('technology');
  });
});
