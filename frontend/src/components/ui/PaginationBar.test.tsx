import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { PaginationBar } from "./PaginationBar";

afterEach(() => cleanup());

describe("PaginationBar", () => {
  it("shows range copy with total count", () => {
    render(
      <PaginationBar
        offset={50}
        pageSize={50}
        itemCount={50}
        totalCount={237}
        onOffsetChange={() => {}}
      />
    );
    expect(screen.getByText("51–100 of 237")).toBeTruthy();
  });

  it("disables Prev at start and Next at end", () => {
    const onOffsetChange = vi.fn();
    const { rerender } = render(
      <PaginationBar
        offset={0}
        pageSize={25}
        itemCount={25}
        totalCount={50}
        onOffsetChange={onOffsetChange}
      />
    );

    expect((screen.getByRole("button", { name: "Prev" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Next" }) as HTMLButtonElement).disabled).toBe(false);

    rerender(
      <PaginationBar
        offset={25}
        pageSize={25}
        itemCount={25}
        totalCount={50}
        onOffsetChange={onOffsetChange}
      />
    );

    expect((screen.getByRole("button", { name: "Prev" }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Next" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("calls onOffsetChange when Next is clicked", () => {
    const onOffsetChange = vi.fn();
    render(
      <PaginationBar
        offset={0}
        pageSize={25}
        itemCount={25}
        totalCount={100}
        onOffsetChange={onOffsetChange}
      />
    );

    screen.getByRole("button", { name: "Next" }).click();
    expect(onOffsetChange).toHaveBeenCalledWith(25);
  });

  it("resets offset when page size changes", () => {
    const onOffsetChange = vi.fn();
    const onPageSizeChange = vi.fn();
    render(
      <PaginationBar
        offset={50}
        pageSize={25}
        itemCount={25}
        totalCount={200}
        onOffsetChange={onOffsetChange}
        onPageSizeChange={onPageSizeChange}
      />
    );

    fireEvent.change(screen.getByDisplayValue("25"), { target: { value: "50" } });
    expect(onPageSizeChange).toHaveBeenCalled();
    expect(onOffsetChange).toHaveBeenCalledWith(0);
  });
});
