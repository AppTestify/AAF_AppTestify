import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "./LoginPage";

const loginMock = vi.fn();
const navigateMock = vi.fn();

vi.mock("../api", () => ({
  login: (...args: unknown[]) => loginMock(...args),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

afterEach(() => {
  cleanup();
  loginMock.mockReset();
  navigateMock.mockReset();
});

function renderLogin() {
  const onAuthed = vi.fn();
  render(
    <MemoryRouter>
      <LoginPage onAuthed={onAuthed} signupEnabled={false} />
    </MemoryRouter>
  );
  return { onAuthed };
}

describe("LoginPage", () => {
  it("renders email and password fields", () => {
    renderLogin();
    expect(screen.getByLabelText(/email/i)).toBeTruthy();
    expect(screen.getByLabelText(/password/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeTruthy();
  });

  it("submits credentials and navigates on success", async () => {
    const user = { id: 1, email: "admin@localhost", is_superadmin: false, is_admin: true, tenant_id: 1, tenant_slug: "default" };
    loginMock.mockResolvedValue({ token_type: "bearer", expires_in: 3600, user });
    const { onAuthed } = renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "admin@localhost" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith("admin@localhost", "secret");
      expect(onAuthed).toHaveBeenCalled();
      expect(navigateMock).toHaveBeenCalledWith("/app", { replace: true });
    });
  });

  it("shows API error message on failure", async () => {
    loginMock.mockRejectedValue(new Error("Invalid credentials"));
    renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "bad@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("Invalid credentials");
    });
  });
});
