import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Table, THead, TBody, TR, TH, TD } from "./Table";

test("renders a semantic table with mono numeric cells", () => {
  render(
    <Table>
      <THead>
        <TR>
          <TH>Model</TH>
          <TH>Disk</TH>
        </TR>
      </THead>
      <TBody>
        <TR>
          <TD mono>large-v3</TD>
          <TD mono num>
            3 GB
          </TD>
        </TR>
      </TBody>
    </Table>,
  );
  expect(screen.getByRole("table")).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "3 GB" })).toHaveClass("font-mono");
});
